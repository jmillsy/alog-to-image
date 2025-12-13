"""
Command-line interface for alog-to-image.
"""

import argparse
import sys
from pathlib import Path
from .renderer import parse_alog, render_alog


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
        
        print(f"Rendering to: {output_path}")
        render_alog(data, output_path, dpi=args.dpi)
        print(f"Rendered image saved to: {output_path}")
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
