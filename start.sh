#!/bin/bash

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it first."
    exit 1
fi

# Check if requirements are installed
if [ -f "requirements.txt" ]; then
    # Check if PyYAML and rich are installed
    if ! python3 -c "import yaml; import rich" &> /dev/null; then
        echo "Installing dependencies..."
        pip3 install -r requirements.txt
    fi
fi

# Run the downloader
echo "Launching ComfyUI CivitAI Downloader..."
python3 download.py "$@"
