#!/bin/bash

echo "🚀 Installing QR Watermarking Tool"
echo "=================================="

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment  
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip setuptools wheel

# Clear cache and install
echo "Installing dependencies..."
pip cache purge 2>/dev/null || true
pip install -r requirements.txt

echo ""
echo "✅ Installation completed!"
echo ""
echo "To start the application:"
echo "source venv/bin/activate"
echo "python app.py"