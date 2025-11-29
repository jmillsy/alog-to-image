#!/bin/bash
# Quick start script to set up and test the alog renderer

echo "🔧 Setting up ALOG to Image Renderer..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "📊 Testing with example file..."
python alog_renderer.py "example/#28_25-11-28_1654.alog" -o "example/output.png"

echo ""
echo "🎉 Done! Check example/output.png for the rendered image."
echo ""
echo "Usage:"
echo "  python alog_renderer.py your_file.alog"
echo "  python alog_renderer.py your_file.alog -o custom_output.png"
echo "  python alog_renderer.py your_file.alog --dpi 300"
