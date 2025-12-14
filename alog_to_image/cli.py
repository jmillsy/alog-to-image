"""
Command-line interface for alog-to-image.
"""

import argparse
import json
import sys
from pathlib import Path
from .renderer import parse_alog, render_alog, extract_roast_stats


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Render Artisan roaster .alog files to PNG images',
        prog='alog-to-image'
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
    parser.add_argument(
        '--json',
        action='store_true',
        default=True,
        help='Output roast statistics in JSON format (default: enabled, use --no-json to disable)'
    )
    parser.add_argument(
        '--no-json',
        action='store_true',
        default=False,
        help='Disable JSON statistics output'
    )
    parser.add_argument(
        '--json-only',
        action='store_true',
        default=False,
        help='Only output JSON statistics without rendering image'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
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
    
    try:
        # Parse and render
        print(f"Parsing alog file: {input_path}")
        data = parse_alog(input_path)
        
        # Render image unless --json-only
        if not args.json_only:
            print(f"Rendering to: {output_path}")
            render_alog(data, output_path, dpi=args.dpi, source_filename=input_path.name)
            print(f"Rendered image saved to: {output_path}")
        
        # Output JSON if requested (default True unless --no-json is set)
        if (args.json and not args.no_json) or args.json_only:
            stats = extract_roast_stats(data, input_path.name)
            print("\nRoast Statistics (JSON):")
            print(json.dumps(stats, indent=2))
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
