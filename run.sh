#!/bin/bash

echo "========================================"
echo "AI Hand Builder - Python Version"
echo "Quick Start Script (Linux/Mac)"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8+ first"
    exit 1
fi

echo "Python found!"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Check if dependencies are installed
python -c "import cv2" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    echo "This may take a few minutes..."
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo ""
fi

# Run the application
echo "========================================"
echo "Starting AI Hand Builder..."
echo "========================================"
echo ""
python main.py

# Deactivate virtual environment
deactivate

echo ""
echo "========================================"
echo "Application closed"
echo "========================================"
