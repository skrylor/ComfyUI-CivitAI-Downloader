#!/bin/bash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Launching ComfyUI CivitAI Downloader...${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if requirements are installed
if [ -f "requirements.txt" ]; then
    # Check if PyYAML and rich are installed
    if ! python3 -c "import yaml; import rich" &> /dev/null; then
        echo "Installing dependencies..."
        pip3 install -r requirements.txt
        if [ $? -ne 0 ]; then
             echo -e "${RED}[ERROR] Failed to install dependencies.${NC}"
             exit 1
        fi
    fi
fi

# Run the downloader
# Pass all arguments to the python script
python3 download.py "$@"

