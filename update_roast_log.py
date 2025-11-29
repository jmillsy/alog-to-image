#!/usr/bin/env python3
"""
Update the roast log markdown file with new roast entries.
Extracts metadata from alog files and maintains a sorted table.
"""

import argparse
import ast
import sys
from pathlib import Path
from datetime import datetime


def parse_alog(filepath):
    """Parse an alog file and extract relevant metadata."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        data = ast.literal_eval(content)
        return data
    except (SyntaxError, ValueError) as e:
        print(f"Error parsing alog file: {e}", file=sys.stderr)
        sys.exit(1)


def extract_metadata(data, alog_path):
    """Extract metadata for the roast log table."""
    computed = data.get('computed', {})
    
    # Batch number and roast date
    batch_prefix = data.get('roastbatchprefix', '#')
    batch_number = data.get('roastbatchnr', 0)
    roast_name = f"{batch_prefix}{batch_number}"
    
    roast_date = data.get('roastdate', '')
    roast_iso_date = data.get('roastisodate', '')
    
    # Total time
    total_time = computed.get('totaltime', 0)
    total_time_min = total_time / 60 if total_time > 0 else 0
    
    # Development percentage
    fcs_time = computed.get('FCs_time', 0)
    drop_time = computed.get('DROP_time', 0)
    development_pct = 0
    
    if fcs_time > 0 and drop_time > 0 and total_time > 0:
        development_time = drop_time - fcs_time
        development_pct = (development_time / total_time) * 100
    
    # Weight and loss
    weight_in = data.get('weight', [0, 0, 'g'])[0]
    weight_out = data.get('weight', [0, 0, 'g'])[1]
    weight_loss = 0
    if weight_in > 0 and weight_out > 0:
        weight_loss = ((weight_in - weight_out) / weight_in) * 100
    
    # Beans
    beans = data.get('beans', '').strip()
    
    return {
        'roast_name': roast_name,
        'batch_number': batch_number,
        'roast_date': roast_date,
        'roast_iso_date': roast_iso_date,
        'total_time_min': total_time_min,
        'development_pct': development_pct,
        'weight_in': weight_in,
        'weight_out': weight_out,
        'weight_loss': weight_loss,
        'beans': beans if beans else 'N/A',
        'alog_path': alog_path
    }


def parse_table_row(line):
    """Parse a markdown table row into metadata dict."""
    if not line.strip() or line.strip().startswith('|---') or line.strip().startswith('| Roast'):
        return None
    
    parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove empty first/last
    if len(parts) < 5:
        return None
    
    try:
        # Extract batch number from roast name (e.g., "#28" -> 28)
        roast_name = parts[0]
        batch_number = int(roast_name.replace('#', '').strip())
        
        # Extract ISO date from the date column (extract YYYY-MM-DD)
        date_text = parts[1]
        # Try to parse date
        try:
            if '-' in date_text:
                date_parts = date_text.split()
                for part in date_parts:
                    if '-' in part and len(part) == 10:  # YYYY-MM-DD format
                        roast_iso_date = part
                        break
                else:
                    roast_iso_date = ''
            else:
                roast_iso_date = ''
        except:
            roast_iso_date = ''
        
        return {
            'roast_name': roast_name,
            'batch_number': batch_number,
            'roast_iso_date': roast_iso_date,
            'raw_line': line
        }
    except (ValueError, IndexError):
        return None


def update_roast_log(log_path, metadata, render_path, repo_url=None):
    """Update the roast log markdown file with new entry."""
    log_file = Path(log_path)
    
    # Read existing entries
    existing_entries = []
    header_lines = []
    
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        in_table = False
        for line in lines:
            if line.strip().startswith('| Roast'):
                in_table = True
                continue
            elif line.strip().startswith('|---'):
                continue
            elif in_table and line.strip().startswith('|'):
                entry = parse_table_row(line)
                if entry:
                    existing_entries.append(entry)
            elif not in_table:
                header_lines.append(line)
    else:
        # Create header
        header_lines = [
            "# Roast Log\n",
            "\n",
            "A chronological log of all coffee roasts.\n",
            "\n"
        ]
    
    # Check if this roast already exists
    batch_number = metadata['batch_number']
    existing_batches = [e['batch_number'] for e in existing_entries]
    
    if batch_number in existing_batches:
        print(f"Roast {metadata['roast_name']} already exists in log, skipping...")
        return False
    
    # Create image URL with proper encoding
    if repo_url:
        # Use raw GitHub content URL with URL encoding
        import urllib.parse
        encoded_path = urllib.parse.quote(render_path)
        image_url = f"{repo_url}/{encoded_path}"
    else:
        # Fallback to relative path with URL encoding
        import urllib.parse
        image_url = urllib.parse.quote(render_path)
    
    # Create new entry row
    new_row = (
        f"| {metadata['roast_name']} "
        f"| {metadata['roast_date']} "
        f"| {metadata['total_time_min']:.1f} min "
        f"| {metadata['development_pct']:.1f}% "
        f"| ![Profile]({image_url}) |\n"
    )
    
    # Add new entry to list
    new_entry = {
        'roast_name': metadata['roast_name'],
        'batch_number': batch_number,
        'roast_iso_date': metadata['roast_iso_date'],
        'raw_line': new_row
    }
    existing_entries.append(new_entry)
    
    # Sort by date (newest first) and batch number
    def sort_key(entry):
        iso_date = entry['roast_iso_date'] if entry['roast_iso_date'] else '1970-01-01'
        batch = entry['batch_number']
        return (iso_date, batch)
    
    existing_entries.sort(key=sort_key, reverse=True)
    
    # Write updated file
    with open(log_file, 'w', encoding='utf-8') as f:
        # Write header
        for line in header_lines:
            f.write(line)
        
        # Write table header
        f.write("| Roast | Date | Time | Dev % | Profile |\n")
        f.write("|-------|------|------|-------|----------|\n")
        
        # Write all entries
        for entry in existing_entries:
            f.write(entry['raw_line'])
    
    print(f"Added {metadata['roast_name']} to roast log")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Update roast log with new alog file entry'
    )
    parser.add_argument(
        'alog_file',
        type=str,
        help='Path to the alog file'
    )
    parser.add_argument(
        'render_path',
        type=str,
        help='Path to the rendered profile image (relative to repo root)'
    )
    parser.add_argument(
        '--log',
        type=str,
        default='roasts.md',
        help='Path to the roast log markdown file (default: roasts.md)'
    )
    parser.add_argument(
        '--repo-url',
        type=str,
        default=None,
        help='Base URL for raw GitHub content (e.g., https://raw.githubusercontent.com/user/repo/refs/heads/main)'
    )
    
    args = parser.parse_args()
    
    # Parse alog file
    print(f"Parsing {args.alog_file}...")
    data = parse_alog(args.alog_file)
    
    # Extract metadata
    metadata = extract_metadata(data, args.alog_file)
    print(f"Extracted metadata for roast {metadata['roast_name']}")
    
    # Update log
    updated = update_roast_log(args.log, metadata, args.render_path, args.repo_url)
    
    if updated:
        print(f"Successfully updated {args.log}")
    
    return 0 if updated else 1


if __name__ == '__main__':
    sys.exit(main())
