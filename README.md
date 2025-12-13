# ALOG to Image

Convert Artisan roaster `.alog` files into beautiful PNG visualizations showing temperature curves and rate of rise (RoR).

[![PyPI version](https://badge.fury.io/py/alog-to-image.svg)](https://badge.fury.io/py/alog-to-image)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 📊 Renders Bean Temperature (BT) and Environment Temperature (ET) curves
- 📈 Calculates and displays Rate of Rise (RoR) with peak detection
- 🎯 Shows roast phases: CHARGE, TP, DRY END, First Crack (FCs/FCe), DROP
- 🏷️ Temperature annotations directly on curves at each event
- 📊 RoR values displayed at key roasting phases
- 📝 Includes metadata: beans, roaster, weight loss, phase durations
- 🤖 Works as CLI tool, Python library, or GitHub Action
- 🎨 High-quality output with customizable DPI

## Installation

### As a Python Package (Recommended)

```bash
pip install alog-to-image
```

### From Source

```bash
git clone https://github.com/jmillsy/alog-to-image.git
cd alog-to-image
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Basic usage - output will be input_name.png
alog-to-image roast.alog

# Specify output path
alog-to-image roast.alog -o output/my_roast.png

# High-resolution output
alog-to-image roast.alog --dpi 300
```

### Python API

```python
from alog_to_image import parse_alog, render_alog

# Parse and render
data = parse_alog('roast.alog')
render_alog(data, 'output.png', dpi=150)
```

### TypeScript/Node.js Integration

Install the package globally or in your project:

```bash
pip install alog-to-image
```

Then use it via subprocess:

```typescript
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function renderAlog(inputPath: string, outputPath: string) {
  try {
    const { stdout, stderr } = await execAsync(
      `alog-to-image "${inputPath}" -o "${outputPath}"`
    );
    console.log(stdout);
    return outputPath;
  } catch (error) {
    console.error('Error rendering alog:', error);
    throw error;
  }
}

// Usage
await renderAlog('roast.alog', 'output.png');
```

Or create a reusable wrapper:

```typescript
class AlogRenderer {
  async render(
    inputPath: string, 
    outputPath: string, 
    options: { dpi?: number } = {}
  ): Promise<string> {
    const dpiFlag = options.dpi ? `--dpi ${options.dpi}` : '';
    const command = `alog-to-image "${inputPath}" -o "${outputPath}" ${dpiFlag}`;
    
    const { stdout } = await execAsync(command);
    console.log(stdout);
    return outputPath;
  }
}

// Usage
const renderer = new AlogRenderer();
await renderer.render('roast.alog', 'output.png', { dpi: 300 });
```

### GitHub Action

Use as a reusable action in your repository:

```yaml
name: Render Alog Files

on:
  push:
    paths:
      - '**.alog'

permissions:
  contents: write

jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: jmillsy/alog-to-image@v1
```

The action will automatically:
- Detect changed `.alog` files
- Render them to `renders/#<batch>.png`
- Update `roasts.md` with embedded images
- Commit the changes

## Output Example

The generated image includes:

**Temperature Chart (Top)**
- Bean Temperature (BT) and Environment Temperature (ET) curves
- Vertical markers for key events (CHARGE, TP, DRY, FCs, FCe, DROP)
- Temperature annotations directly on the BT curve at each event
- Special event markers (gas changes, etc.)

**Rate of Rise Chart (Bottom)**
- RoR curve showing heating rate over time
- Peak RoR highlighted with value
- RoR values displayed at each phase marker
- Same event markers as temperature chart

**Metadata Box**
- Bean origin and roaster type
- Weight in/out and loss percentage
- Total roast time and development percentage
- Phase durations (drying, maillard, development)

## Development

### Setup Development Environment

```bash
git clone https://github.com/jmillsy/alog-to-image.git
cd alog-to-image
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Run Tests

```bash
# Test CLI
alog-to-image example/#28_25-11-28_1654.alog -o test.png

# Test Python API
python -c "from alog_to_image import parse_alog, render_alog; \
           data = parse_alog('example/#28_25-11-28_1654.alog'); \
           render_alog(data, 'test.png')"
```

### Build Package

```bash
pip install build
python -m build
```

This creates distribution files in `dist/`:
- `alog_to_image-1.0.0-py3-none-any.whl` (wheel)
- `alog-to-image-1.0.0.tar.gz` (source)

### Publish to PyPI

```bash
pip install twine
twine upload dist/*
```

## API Reference

### `parse_alog(filepath)`

Parse an .alog file and return the data dictionary.

**Parameters:**
- `filepath` (str): Path to the .alog file

**Returns:**
- `dict`: Parsed alog data

**Raises:**
- `ValueError`: If file cannot be parsed

### `calculate_ror(times, temps, window=30)`

Calculate Rate of Rise for temperature data.

**Parameters:**
- `times` (list): Time values in seconds
- `temps` (list): Temperature values
- `window` (int): Time window for RoR calculation in seconds (default: 30)

**Returns:**
- `list`: RoR values in degrees per minute

### `render_alog(data, output_path, dpi=150)`

Render alog data to a PNG image.

**Parameters:**
- `data` (dict): Parsed alog data
- `output_path` (str): Path for output PNG
- `dpi` (int): Image resolution (default: 150)

**Raises:**
- `ValueError`: If no valid temperature data found

## Requirements

- Python 3.8+
- matplotlib >= 3.5.0

## License

MIT License - see [LICENSE](LICENSE) file for details

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Credits

Created by [John Mills](https://github.com/jmillsy)

For use with [Artisan Roaster Software](https://github.com/artisan-roaster-scope/artisan)
