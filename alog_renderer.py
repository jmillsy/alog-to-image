#!/usr/bin/env python3
"""
ALOG File Renderer
Converts Artisan roaster .alog files to PNG images with temperature and RoR curves.
"""

import argparse
import ast
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta


def parse_alog(filepath):
    """
    Parse an .alog file and return the Python dictionary.
    
    Args:
        filepath: Path to the .alog file
        
    Returns:
        Dictionary containing roast data
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        data = ast.literal_eval(content)
        return data
    except (SyntaxError, ValueError) as e:
        print(f"Error parsing alog file: {e}", file=sys.stderr)
        sys.exit(1)


def calculate_ror(times, temps, window=30):
    """
    Calculate Rate of Rise (RoR) for temperature data.
    
    Args:
        times: List of time values in seconds
        temps: List of temperature values
        window: Time window in seconds for RoR calculation (default 30s)
        
    Returns:
        List of RoR values (degrees per minute)
    """
    ror = []
    
    for i in range(len(temps)):
        # Find data points within the window
        lookback_time = times[i] - window
        
        # Find earliest index within window
        start_idx = i
        for j in range(i - 1, -1, -1):
            if times[j] >= lookback_time:
                start_idx = j
            else:
                break
        
        # Calculate RoR if we have enough data
        if start_idx < i and temps[i] >= 0 and temps[start_idx] >= 0:
            time_diff = times[i] - times[start_idx]
            temp_diff = temps[i] - temps[start_idx]
            
            if time_diff > 0:
                # Convert to degrees per minute
                ror_value = (temp_diff / time_diff) * 60
                ror.append(ror_value)
            else:
                ror.append(0)
        else:
            ror.append(0)
    
    return ror


def render_alog(data, output_path, dpi=150):
    """
    Render the alog data to a PNG image.
    
    Args:
        data: Dictionary containing parsed alog data
        output_path: Path where PNG should be saved
        dpi: DPI for output image (default 150)
    """
    # Extract time series data
    timex = data.get('timex', [])
    temp1 = data.get('temp1', [])
    temp2 = data.get('temp2', [])
    
    # Detect which temp is BT vs ET based on computed data
    # BT typically drops when beans are charged, ET stays higher
    computed = data.get('computed', {})
    charge_bt = computed.get('CHARGE_BT')
    charge_et = computed.get('CHARGE_ET')
    
    # If we have computed data, use it to determine which is which
    if charge_bt is not None and charge_et is not None and len(temp1) > 0 and len(temp2) > 0:
        # Find temps around charge time (index 8-10 typically)
        charge_idx = min(10, len(temp1) - 1)
        temp1_at_charge = temp1[charge_idx] if temp1[charge_idx] >= 0 else temp1[0]
        temp2_at_charge = temp2[charge_idx] if temp2[charge_idx] >= 0 else temp2[0]
        
        # Match temps to computed values (within tolerance)
        temp1_matches_bt = abs(temp1_at_charge - charge_bt) < abs(temp1_at_charge - charge_et)
        temp2_matches_bt = abs(temp2_at_charge - charge_bt) < abs(temp2_at_charge - charge_et)
        
        if temp2_matches_bt:
            bt_temps = temp2
            et_temps = temp1
        else:
            bt_temps = temp1
            et_temps = temp2
    else:
        # Fallback: assume temp1=BT, temp2=ET (original convention)
        # But check which one is typically lower (BT behavior)
        if len(temp1) > 10 and len(temp2) > 10:
            # BT typically has lower average and more dramatic swings
            avg_temp1 = sum(t for t in temp1[:50] if t >= 0) / max(1, sum(1 for t in temp1[:50] if t >= 0))
            avg_temp2 = sum(t for t in temp2[:50] if t >= 0) / max(1, sum(1 for t in temp2[:50] if t >= 0))
            
            if avg_temp2 < avg_temp1:
                bt_temps = temp2
                et_temps = temp1
            else:
                bt_temps = temp1
                et_temps = temp2
        else:
            bt_temps = temp1
            et_temps = temp2
    
    # Filter out invalid temperature readings (-1.0)
    valid_data = []
    for i in range(len(timex)):
        bt = bt_temps[i] if i < len(bt_temps) else -1
        et = et_temps[i] if i < len(et_temps) else -1
        
        # Keep data point if at least one temp is valid
        if bt >= 0 or et >= 0:
            valid_data.append((timex[i], bt, et))
    
    if not valid_data:
        print("No valid temperature data found in alog file", file=sys.stderr)
        sys.exit(1)
    
    # Unpack valid data
    times, bt_temps, et_temps = zip(*valid_data)
    
    # Convert times to minutes for display
    times_min = [t / 60 for t in times]
    
    # Calculate RoR for BT
    bt_ror = calculate_ror(list(times), list(bt_temps))
    
    # Find turning point (TP) to exclude initial charge RoR
    computed = data.get('computed', {})
    tp_time = computed.get('TP_time', 0)  # Time in seconds
    tp_idx = 0
    
    # Find the index closest to TP time
    if tp_time > 0:
        for i, t in enumerate(times):
            if t >= tp_time:
                tp_idx = i
                break
    
    # Set RoR to 0 before turning point (meaningless charge data)
    bt_ror_filtered = [0 if i < tp_idx else ror for i, ror in enumerate(bt_ror)]
    
    # Extract roast metadata
    roast_title = data.get('title', 'Roast Profile')
    roast_date = data.get('roastdate', '')
    beans = data.get('beans', '')
    roaster = data.get('roastertype', '')
    weight_in = data.get('weight', [0, 0, 'g'])[0]
    weight_out = data.get('weight', [0, 0, 'g'])[1]
    
    # Extract phases (DRY, FCs, FCe, DROP)
    phases = data.get('phases', [])
    timeindex = data.get('timeindex', [])
    
    # Extract special events (gas changes, etc.)
    specialevents = data.get('specialevents', [])  # Indices into timex
    specialevents_strings = data.get('specialeventsStrings', [])
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(f'{roast_title} - {roast_date}', fontsize=16, fontweight='bold')
    
    # Plot 1: Temperature curves
    ax1.plot(times_min, bt_temps, 'b-', linewidth=2, label='BT (Bean Temp)')
    ax1.plot(times_min, et_temps, 'r-', linewidth=2, label='ET (Env Temp)')
    
    ax1.set_ylabel('Temperature (°F)', fontsize=12)
    ax1.set_title('Temperature Profile', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # Add CHARGE marker with temperature annotation
    charge_bt = computed.get('CHARGE_BT', 0)
    if timeindex and len(timeindex) > 0 and timeindex[0] > 0:
        charge_idx = timeindex[0]
        if charge_idx < len(times_min):
            ax1.axvline(x=times_min[charge_idx], color='brown', linestyle=':', 
                       linewidth=2, alpha=0.8, label='CHARGE')
            if charge_bt > 0:
                ax1.annotate(f'{charge_bt:.1f}°F', 
                           xy=(times_min[charge_idx], charge_bt),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=9, color='brown', fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                   edgecolor='brown', alpha=0.7))
    
    # Add Turning Point marker with temperature annotation
    tp_bt = computed.get('TP_BT', 0)
    if tp_time > 0 and tp_idx < len(times_min):
        ax1.axvline(x=times_min[tp_idx], color='gray', linestyle=':', 
                   linewidth=2, alpha=0.6, label='TP')
        if tp_bt > 0:
            ax1.annotate(f'{tp_bt:.1f}°F', 
                       xy=(times_min[tp_idx], tp_bt),
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=9, color='gray', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                               edgecolor='gray', alpha=0.7))
    
    # Add phase markers using computed times with temperature annotations
    phase_events = [
        ('DRY_time', 'DRY_END_BT', 'DRY END', 'orange'),
        ('FCs_time', 'FCs_BT', 'FCs', 'green'),
        ('FCe_time', 'FCe_BT', 'FCe', 'purple'),
        ('DROP_time', 'DROP_BT', 'DROP', 'red')
    ]
    
    for event_key, temp_key, name, color in phase_events:
        event_time = computed.get(event_key, 0)
        event_temp = computed.get(temp_key, 0)
        if event_time > 0:
            event_time_min = event_time / 60
            # Find closest time index
            if event_time_min <= times_min[-1]:
                ax1.axvline(x=event_time_min, color=color, linestyle='--', 
                           linewidth=1.5, alpha=0.7, label=name)
                if event_temp > 0:
                    ax1.annotate(f'{event_temp:.1f}°F', 
                               xy=(event_time_min, event_temp),
                               xytext=(5, -15), textcoords='offset points',
                               fontsize=9, color=color, fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                       edgecolor=color, alpha=0.7))
    
    ax1.legend(loc='upper left', fontsize=9, ncol=2)
    
    # Plot 2: Rate of Rise (RoR)
    ax2.plot(times_min, bt_ror_filtered, 'g-', linewidth=2, label='BT RoR')
    ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    
    ax2.set_xlabel('Time (minutes)', fontsize=12)
    ax2.set_ylabel('Rate of Rise (°F/min)', fontsize=12)
    ax2.set_title('Rate of Rise', fontsize=14)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right', fontsize=10)
    
    # Set Y-axis minimum to 0 to better show the gradual decline
    # Calculate max RoR for upper bound with some padding
    max_ror = max(bt_ror_filtered) if bt_ror_filtered else 10
    ax2.set_ylim(bottom=0, top=max_ror * 1.1)
    
    # Find and mark peak RoR
    if bt_ror_filtered:
        peak_ror_idx = bt_ror_filtered.index(max_ror)
        peak_ror_time = times_min[peak_ror_idx]
        ax2.plot(peak_ror_time, max_ror, 'r*', markersize=15, zorder=5)
        ax2.annotate(f'Peak: {max_ror:.1f}°F/min', 
                   xy=(peak_ror_time, max_ror),
                   xytext=(10, 10), textcoords='offset points',
                   fontsize=9, color='red', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                           edgecolor='red', alpha=0.8),
                   arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
    
    # Add phase markers to RoR plot with RoR value annotations
    for event_key, temp_key, name, color in phase_events:
        event_time = computed.get(event_key, 0)
        if event_time > 0:
            event_time_min = event_time / 60
            if event_time_min <= times_min[-1]:
                # Find closest index for this time
                event_idx = min(range(len(times_min)), 
                              key=lambda i: abs(times_min[i] - event_time_min))
                event_ror = bt_ror_filtered[event_idx]
                
                ax2.axvline(x=event_time_min, color=color, linestyle='--', 
                           linewidth=1.5, alpha=0.7)
                
                # Add RoR value annotation at the event point
                if event_ror > 0:  # Only show if RoR is meaningful
                    ax2.annotate(f'{event_ror:.1f}°F/min', 
                               xy=(event_time_min, event_ror),
                               xytext=(5, 5), textcoords='offset points',
                               fontsize=8, color=color, fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                       edgecolor=color, alpha=0.7))
    
    # Add special events to RoR plot
    if specialevents and specialevents_strings:
        for i, event_idx in enumerate(specialevents):
            if 0 <= event_idx < len(times_min) and i < len(specialevents_strings):
                event_label = specialevents_strings[i]
                if event_label and event_label.strip():
                    ax2.axvline(x=times_min[event_idx], color='blue', linestyle=':', 
                               linewidth=1, alpha=0.4)
    
    # Calculate development percentage
    fcs_time = computed.get('FCs_time', 0)
    drop_time = computed.get('DROP_time', 0)
    total_time = computed.get('totaltime', 0)
    development_pct = 0
    
    if fcs_time > 0 and drop_time > 0 and total_time > 0:
        development_time = drop_time - fcs_time
        development_pct = (development_time / total_time) * 100
    
    # Add metadata text box
    metadata_text = []
    if beans:
        metadata_text.append(f'Beans: {beans}')
    if roaster:
        metadata_text.append(f'Roaster: {roaster}')
    if weight_in > 0:
        metadata_text.append(f'Weight: {weight_in}g → {weight_out}g')
        if weight_out > 0:
            loss_pct = ((weight_in - weight_out) / weight_in) * 100
            metadata_text.append(f'Loss: {loss_pct:.1f}%')
    if total_time > 0:
        metadata_text.append(f'Total Time: {total_time/60:.1f} min')
    if development_pct > 0:
        metadata_text.append(f'Development: {development_pct:.1f}%')
    
    # Add phase durations and percentages
    phase_durations = computed.get('phase_durations_s', {})
    phase_percentages = computed.get('phase_percentages', {})
    
    drying_duration = phase_durations.get('drying', 0)
    maillard_duration = phase_durations.get('maillard', 0)
    dev_duration = phase_durations.get('development', 0)
    
    drying_pct = phase_percentages.get('drying', 0)
    maillard_pct = phase_percentages.get('maillard', 0)
    dev_pct = phase_percentages.get('development', 0)
    
    if drying_duration > 0:
        metadata_text.append(f'Drying: {drying_duration}s ({drying_pct:.1f}%)')
    if maillard_duration > 0:
        metadata_text.append(f'Maillard: {maillard_duration}s ({maillard_pct:.1f}%)')
    if dev_duration > 0:
        metadata_text.append(f'Dev: {dev_duration}s ({dev_pct:.1f}%)')
    
    if metadata_text:
        fig.text(0.99, 0.01, '\n'.join(metadata_text), 
                ha='right', va='bottom', fontsize=9, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"Rendered image saved to: {output_path}")
    plt.close()


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Render Artisan roaster .alog files to PNG images'
    )
    parser.add_argument(
        'input',
        type=str,
        help='Path to the input .alog file'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Path for the output PNG file (default: input_name.png)'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=150,
        help='DPI for output image (default: 150)'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.png')
    
    # Parse and render
    print(f"Parsing alog file: {input_path}")
    data = parse_alog(input_path)
    
    print(f"Rendering to: {output_path}")
    render_alog(data, output_path, dpi=args.dpi)


if __name__ == '__main__':
    main()
