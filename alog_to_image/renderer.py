"""
Core rendering logic for ALOG files.
"""

import ast
import sys
from pathlib import Path
import matplotlib.pyplot as plt


def parse_alog(filepath):
    """
    Parse an .alog file and return the Python dictionary.
    
    Args:
        filepath: Path to the .alog file
        
    Returns:
        Dictionary containing roast data
        
    Raises:
        ValueError: If file cannot be parsed
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        data = ast.literal_eval(content)
        return data
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"Error parsing alog file: {e}")


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


def render_alog(data, output_path, dpi=150, source_filename=None):
    """
    Render the alog data to a PNG image.
    
    Args:
        data: Dictionary containing parsed alog data
        output_path: Path where PNG should be saved
        dpi: DPI for output image (default 150)
        source_filename: Optional filename to display on the image
        
    Raises:
        ValueError: If no valid temperature data found
    """
    # Extract time series data
    timex = data.get('timex', [])
    temp1 = data.get('temp1', [])
    temp2 = data.get('temp2', [])
    
    # Get DROP time but DON'T truncate yet - do it after valid data filtering
    computed = data.get('computed', {})
    drop_time = computed.get('DROP_time', 0)
    
    # Detect which temp is BT vs ET based on computed data
    # BT typically drops when beans are charged, ET stays higher
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
        raise ValueError("No valid temperature data found in alog file")
    
    # Unpack valid data
    times, bt_temps, et_temps = zip(*valid_data)
    
    # NOW apply DROP cutoff AFTER filtering valid data
    drop_idx = len(times)
    if drop_time > 0:
        for i, t in enumerate(times):
            if t >= drop_time:
                drop_idx = i + 1
                break
    
    # Truncate to DROP
    times = times[:drop_idx]
    bt_temps = bt_temps[:drop_idx]
    et_temps = et_temps[:drop_idx]
    
    # Also truncate timex for later use
    timex = timex[:drop_idx]
    
    # Extract exhaust and ambient temps AFTER determining drop_idx
    extratemp1 = data.get('extratemp1', [[]])[0][:drop_idx] if data.get('extratemp1') else []
    extratemp2 = data.get('extratemp2', [[]])[0][:drop_idx] if data.get('extratemp2') else []
    
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
    total_time = computed.get('totaltime', 0)
    
    # Extract phases
    phases = data.get('phases', [])
    timeindex = data.get('timeindex', [])
    
    # Extract special events (gas changes, etc.)
    specialevents = data.get('specialevents', [])  # Indices into timex
    specialevents_strings = data.get('specialeventsStrings', [])
    
    # Create figure with subplots (14x11 inches for extra space)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 11), sharex=True)
    fig.suptitle(f'{roast_title} - {roast_date}', fontsize=16, fontweight='bold')
    
    # Add filename in top-left corner if provided
    if source_filename:
        fig.text(0.01, 0.99, f'File: {source_filename}', 
                ha='left', va='top', fontsize=8, 
                style='italic', color='gray',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', 
                         edgecolor='lightgray', alpha=0.7))
    
    # Plot 1: Temperature curves
    ax1.plot(times_min, bt_temps, 'b-', linewidth=2, label='BT (Bean Temp)')
    ax1.plot(times_min, et_temps, 'r-', linewidth=2, label='ET (Env Temp)')
    
    # Add exhaust temp if available
    if extratemp1 and any(t > 0 for t in extratemp1):
        exhaust_times = [times_min[i] for i in range(min(len(times_min), len(extratemp1))) if extratemp1[i] > 0]
        exhaust_temps = [t for t in extratemp1 if t > 0]
        if exhaust_times:
            ax1.plot(exhaust_times, exhaust_temps, 'm-', linewidth=1.5, alpha=0.6, label='Exhaust Temp')
    
    ax1.set_ylabel('Temperature (°F)', fontsize=12)
    ax1.set_title('Temperature Profile', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # Add phase bars at top of temperature plot
    dry_end_time = computed.get('DRY_time', 0)
    fcs_time = computed.get('FCs_time', 0)
    
    phase_percentages = computed.get('phase_percentages', {})
    drying_pct = phase_percentages.get('drying', 0)
    maillard_pct = phase_percentages.get('maillard', 0)
    dev_pct = phase_percentages.get('development', 0)
    
    # Get current y-axis limits and extend upper limit for phase bars
    y_min, y_max = ax1.get_ylim()
    phase_bar_height = (y_max - y_min) * 0.05  # 5% of plot height
    
    # Extend y-axis to make room for phase bars at top
    ax1.set_ylim(y_min, y_max + phase_bar_height * 1.5)
    y_min, y_max = ax1.get_ylim()  # Get updated limits
    
    phase_bar_y = y_max - phase_bar_height * 0.7  # Position near top
    
    dry_end_min = dry_end_time / 60 if dry_end_time > 0 else 0
    fcs_min = fcs_time / 60 if fcs_time > 0 else 0
    drop_min = drop_time / 60 if drop_time > 0 else times_min[-1]
    
    if dry_end_min > 0:
        drying_width = dry_end_min
        ax1.barh(phase_bar_y, drying_width, height=phase_bar_height, 
                left=0, color='orange', alpha=0.3, edgecolor='orange', linewidth=1.5, zorder=10)
        if drying_pct > 0:
            ax1.text(drying_width / 2, phase_bar_y, f'Drying\n{drying_pct:.1f}%', 
                    ha='center', va='center', fontsize=9, fontweight='bold', 
                    color='darkorange', zorder=11)
    
    if fcs_min > dry_end_min > 0:
        maillard_width = fcs_min - dry_end_min
        ax1.barh(phase_bar_y, maillard_width, height=phase_bar_height, 
                left=dry_end_min, color='brown', alpha=0.3, edgecolor='brown', linewidth=1.5, zorder=10)
        if maillard_pct > 0:
            ax1.text(dry_end_min + maillard_width / 2, phase_bar_y, f'Maillard\n{maillard_pct:.1f}%', 
                    ha='center', va='center', fontsize=9, fontweight='bold', 
                    color='saddlebrown', zorder=11)
    
    if drop_min > fcs_min > 0:
        dev_width = drop_min - fcs_min
        ax1.barh(phase_bar_y, dev_width, height=phase_bar_height, 
                left=fcs_min, color='green', alpha=0.3, edgecolor='green', linewidth=1.5, zorder=10)
        if dev_pct > 0:
            ax1.text(fcs_min + dev_width / 2, phase_bar_y, f'Development\n{dev_pct:.1f}%', 
                    ha='center', va='center', fontsize=9, fontweight='bold', 
                    color='darkgreen', zorder=11)
    
    # Add event markers WITHOUT labels (labels go on x-axis between plots)
    charge_bt = computed.get('CHARGE_BT', 0)
    if timeindex and len(timeindex) > 0 and timeindex[0] > 0:
        charge_idx = timeindex[0]
        if charge_idx < len(times_min):
            ax1.axvline(x=times_min[charge_idx], color='brown', linestyle=':', 
                       linewidth=2, alpha=0.8)
            if charge_bt > 0:
                ax1.annotate(f'{charge_bt:.1f}°F', 
                           xy=(times_min[charge_idx], charge_bt),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=9, color='brown', fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                   edgecolor='brown', alpha=0.7))
    
    tp_time = computed.get('TP_time', 0)
    tp_idx = 0
    tp_bt = computed.get('TP_BT', 0)
    if tp_time > 0:
        for i, t in enumerate(times):
            if t >= tp_time:
                tp_idx = i
                break
        if tp_idx < len(times_min):
            ax1.axvline(x=times_min[tp_idx], color='gray', linestyle=':', 
                       linewidth=2, alpha=0.6)
            if tp_bt > 0:
                ax1.annotate(f'{tp_bt:.1f}°F', 
                           xy=(times_min[tp_idx], tp_bt),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=9, color='gray', fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                   edgecolor='gray', alpha=0.7))
    
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
            if event_time_min <= times_min[-1]:
                ax1.axvline(x=event_time_min, color=color, linestyle='--', 
                           linewidth=1.5, alpha=0.7)
                if event_temp > 0:
                    ax1.annotate(f'{event_temp:.1f}°F', 
                               xy=(event_time_min, event_temp),
                               xytext=(5, -15), textcoords='offset points',
                               fontsize=9, color=color, fontweight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                       edgecolor=color, alpha=0.7))
    
    # Move legend outside plot area
    ax1.legend(loc='upper left', bbox_to_anchor=(0, 1.12), ncol=4, fontsize=9, frameon=False)
    
    # Plot 2: Rate of Rise (RoR)
    ax2.plot(times_min, bt_ror_filtered, 'g-', linewidth=2, label='BT RoR')
    ax2.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    
    ax2.set_xlabel('Time (minutes)', fontsize=12)
    ax2.set_ylabel('Rate of Rise (°F/min)', fontsize=12)
    ax2.set_title('Rate of Rise', fontsize=14)
    ax2.grid(True, alpha=0.3)
    
    # Set Y-axis minimum to 0
    max_ror = max(bt_ror_filtered) if bt_ror_filtered else 10
    ax2.set_ylim(bottom=0, top=max_ror * 1.1)
    
    # Find and mark peak RoR
    if bt_ror_filtered and max_ror > 0:
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
    
    # Move legend outside plot area
    ax2.legend(loc='upper right', bbox_to_anchor=(1, 1.05), fontsize=9, frameon=False)
    
    # Add event labels on x-axis BETWEEN the two plots
    event_labels = []
    if timeindex and len(timeindex) > 0 and timeindex[0] > 0:
        charge_idx = timeindex[0]
        if charge_idx < len(times_min):
            event_labels.append((times_min[charge_idx], 'CHARGE', 'brown'))
    
    if tp_time > 0 and tp_idx < len(times_min):
        event_labels.append((times_min[tp_idx], 'TP', 'gray'))
    
    for event_key, temp_key, name, color in phase_events:
        event_time = computed.get(event_key, 0)
        if event_time > 0:
            event_time_min = event_time / 60
            if event_time_min <= times_min[-1]:
                event_labels.append((event_time_min, name, color))
    
    # Position labels between the plots (just below ax1, above ax2)
    ax1_bottom = ax1.get_position().y0
    for event_time, label, color in event_labels:
        fig.text((event_time / times_min[-1]) * 0.88 + 0.09, ax1_bottom - 0.02, label,
                ha='center', va='top', fontsize=9, fontweight='bold',
                color=color, bbox=dict(boxstyle='round,pad=0.3', 
                facecolor='white', edgecolor=color, alpha=0.8))
    
    # Extract gas changes and build Roast Details section
    specialevents = data.get('specialevents', [])
    specialeventsStrings = data.get('specialeventsStrings', [])
    specialeventsvalue = data.get('specialeventsvalue', [])
    
    # Get charge time for relative time calculations
    charge_time = 0
    if timeindex and len(timeindex) > 0 and timeindex[0] > 0:
        charge_idx = timeindex[0]
        if charge_idx < len(timex):
            charge_time = timex[charge_idx]
    
    # Infer charge gas from specialeventsvalue[0]
    charge_gas = "Unknown"
    if specialeventsvalue and len(specialeventsvalue) > 0:
        gas_value = specialeventsvalue[0]
        if gas_value < 1.3:
            charge_gas = "5"
        elif gas_value < 1.8:
            charge_gas = "10"
        elif gas_value < 2.3:
            charge_gas = "15"
        elif gas_value < 2.8:
            charge_gas = "20"
        elif gas_value < 3.3:
            charge_gas = "25"
        elif gas_value < 3.8:
            charge_gas = "30"
        else:
            charge_gas = "35+"
    
    # Build chronological timeline of events
    timeline_events = []
    
    # Add charge event with gas and temperature
    if charge_time > 0:
        charge_bt_temp = computed.get('CHARGE_BT', 0)
        if charge_bt_temp > 0:
            timeline_events.append((0, f"CHARGE (Gas: {charge_gas}mbar, BT: {charge_bt_temp:.1f}°F)"))
        else:
            timeline_events.append((0, f"CHARGE (Gas: {charge_gas}mbar)"))
    
    # Add roast phase events with temperatures
    event_times = [
        ('TP_time', 'TP', 'TP_BT'),
        ('DRY_time', 'DRY END', 'DRY_END_BT'),
        ('FCs_time', 'FCs', 'FCs_BT'),
        ('FCe_time', 'FCe', 'FCe_BT'),
        ('DROP_time', 'DROP', 'DROP_BT')
    ]
    
    for event_key, event_name, temp_key in event_times:
        event_time = computed.get(event_key, 0)
        if event_time > 0:
            rel_time = event_time - charge_time
            event_temp = computed.get(temp_key, 0)
            if event_temp > 0:
                timeline_events.append((rel_time, f"{event_name} (BT: {event_temp:.1f}°F)"))
            else:
                timeline_events.append((rel_time, event_name))
    
    # Add gas changes
    for i, event_idx in enumerate(specialevents):
        if event_idx < len(timex) and i < len(specialeventsStrings):
            gas_label = specialeventsStrings[i]
            if gas_label and gas_label.strip():
                event_time = timex[event_idx]
                rel_time = event_time - charge_time
                timeline_events.append((rel_time, f"Gas → {gas_label}mbar"))
    
    # Sort chronologically
    timeline_events.sort(key=lambda x: x[0])
    
    # Build Roast Details text
    roast_details = []
    
    # Add metadata section
    if beans:
        roast_details.append(f'Beans: {beans}')
    if roaster:
        roast_details.append(f'Roaster: {roaster}')
    if weight_in > 0:
        roast_details.append(f'Weight: {weight_in}g → {weight_out}g')
        if weight_out > 0:
            loss_pct = ((weight_in - weight_out) / weight_in) * 100
            roast_details.append(f'Loss: {loss_pct:.1f}%')
    if total_time > 0:
        roast_details.append(f'Total Time: {total_time/60:.1f} min')
    
    # Add phase durations
    phase_durations = computed.get('phase_durations_s', {})
    drying_duration = phase_durations.get('drying', 0)
    maillard_duration = phase_durations.get('maillard', 0)
    dev_duration = phase_durations.get('development', 0)
    
    if drying_duration > 0:
        roast_details.append(f'Drying: {drying_duration}s ({drying_pct:.1f}%)')
    if maillard_duration > 0:
        roast_details.append(f'Maillard: {maillard_duration}s ({maillard_pct:.1f}%)')
    if dev_duration > 0:
        roast_details.append(f'Development: {dev_duration}s ({dev_pct:.1f}%)')
    
    # Add separator and timeline
    if timeline_events:
        roast_details.append('')  # Blank line
        roast_details.append('Timeline:')
        for rel_time, event_desc in timeline_events:
            time_str = f"{int(rel_time // 60)}:{int(rel_time % 60):02d}"
            roast_details.append(f"  {time_str} - {event_desc}")
    
    # Display single Roast Details box, left-aligned with plot
    if roast_details:
        ax2_left = ax2.get_position().x0
        fig.text(ax2_left, 0.01, '\n'.join(roast_details), 
                ha='left', va='bottom', fontsize=8, family='monospace',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # Adjust layout and save (increase bottom margin for text box)
    plt.tight_layout(rect=[0, 0.20, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()


def extract_roast_stats(data, filename=None):
    """
    Extract roast statistics from parsed alog data.
    
    Args:
        data: Dictionary containing parsed alog data
        filename: Optional source filename
        
    Returns:
        Dictionary containing roast statistics in a structured format
    """
    computed = data.get('computed', {})
    timex = data.get('timex', [])
    
    # Extract basic metadata
    stats = {
        'file': filename,
        'title': data.get('title', 'Unknown'),
        'roast_date': data.get('roastdate', ''),
        'beans': data.get('beans', ''),
        'roaster': data.get('roastertype', ''),
        'weight': {
            'in': data.get('weight', [0, 0, 'g'])[0],
            'out': data.get('weight', [0, 0, 'g'])[1],
            'unit': data.get('weight', [0, 0, 'g'])[2],
            'loss_percent': 0
        },
        'total_time_seconds': computed.get('totaltime', 0),
        'total_time_formatted': '',
        'phases': {},
        'events': [],
        'gas_changes': []
    }
    
    # Calculate weight loss
    weight_in = stats['weight']['in']
    weight_out = stats['weight']['out']
    if weight_in > 0 and weight_out > 0:
        stats['weight']['loss_percent'] = round(((weight_in - weight_out) / weight_in) * 100, 1)
    
    # Format total time
    total_time = stats['total_time_seconds']
    if total_time > 0:
        stats['total_time_formatted'] = f"{int(total_time // 60)}:{int(total_time % 60):02d}"
    
    # Extract phase information
    phase_durations = computed.get('phase_durations_s', {})
    phase_percentages = computed.get('phase_percentages', {})
    
    for phase_name in ['drying', 'maillard', 'development']:
        duration = phase_durations.get(phase_name, 0)
        percentage = phase_percentages.get(phase_name, 0)
        stats['phases'][phase_name] = {
            'duration_seconds': duration,
            'duration_formatted': f"{int(duration // 60)}:{int(duration % 60):02d}" if duration > 0 else "0:00",
            'percentage': round(percentage, 1)
        }
    
    # Extract events with times and temperatures
    timeindex = data.get('timeindex', [])
    specialeventsvalue = data.get('specialeventsvalue', [])
    
    # Get charge time for relative calculations
    charge_time = 0
    if timeindex and len(timeindex) > 0 and timeindex[0] > 0:
        charge_idx = timeindex[0]
        if charge_idx < len(timex):
            charge_time = timex[charge_idx]
    
    # Infer charge gas
    charge_gas = "Unknown"
    if specialeventsvalue and len(specialeventsvalue) > 0:
        gas_value = specialeventsvalue[0]
        if gas_value < 1.3:
            charge_gas = "5"
        elif gas_value < 1.8:
            charge_gas = "10"
        elif gas_value < 2.3:
            charge_gas = "15"
        elif gas_value < 2.8:
            charge_gas = "20"
        elif gas_value < 3.3:
            charge_gas = "25"
        elif gas_value < 3.8:
            charge_gas = "30"
        else:
            charge_gas = "35+"
    
    # Add charge event
    charge_bt = computed.get('CHARGE_BT', 0)
    stats['events'].append({
        'name': 'CHARGE',
        'time_seconds': 0,
        'time_formatted': '0:00',
        'temperature_f': round(charge_bt, 1) if charge_bt > 0 else None,
        'gas_mbar': charge_gas
    })
    
    # Add roast phase events
    event_list = [
        ('TP_time', 'TP', 'TP_BT'),
        ('DRY_time', 'DRY_END', 'DRY_END_BT'),
        ('FCs_time', 'FCs', 'FCs_BT'),
        ('FCe_time', 'FCe', 'FCe_BT'),
        ('DROP_time', 'DROP', 'DROP_BT')
    ]
    
    for event_key, event_name, temp_key in event_list:
        event_time = computed.get(event_key, 0)
        if event_time > 0:
            rel_time = event_time - charge_time
            event_temp = computed.get(temp_key, 0)
            stats['events'].append({
                'name': event_name,
                'time_seconds': int(rel_time),
                'time_formatted': f"{int(rel_time // 60)}:{int(rel_time % 60):02d}",
                'temperature_f': round(event_temp, 1) if event_temp > 0 else None
            })
    
    # Extract gas changes
    specialevents = data.get('specialevents', [])
    specialeventsStrings = data.get('specialeventsStrings', [])
    
    for i, event_idx in enumerate(specialevents):
        if event_idx < len(timex) and i < len(specialeventsStrings):
            gas_label = specialeventsStrings[i]
            if gas_label and gas_label.strip():
                event_time = timex[event_idx]
                rel_time = event_time - charge_time
                stats['gas_changes'].append({
                    'time_seconds': int(rel_time),
                    'time_formatted': f"{int(rel_time // 60)}:{int(rel_time % 60):02d}",
                    'gas_mbar': gas_label
                })
    
    # Sort events chronologically
    stats['events'].sort(key=lambda x: x['time_seconds'])
    stats['gas_changes'].sort(key=lambda x: x['time_seconds'])
    
    return stats
