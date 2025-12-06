#/usr/bin/env bash

set -e  # Exit on error

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="$PROJECT_DIR/venv"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
INSTALLED_REQUIREMENTS_FILE="$VENV_DIR/installed-requirements.txt"
ENV_FILE="$PROJECT_DIR/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Check if dependencies need to be installed
NEED_INSTALL=false
if [ ! -f "$INSTALLED_REQUIREMENTS_FILE" ]; then
    NEED_INSTALL=true
elif ! cmp -s "$REQUIREMENTS_FILE" "$INSTALLED_REQUIREMENTS_FILE"; then
    NEED_INSTALL=true
fi

if [ "$NEED_INSTALL" = true ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -r "$REQUIREMENTS_FILE"
    cp "$REQUIREMENTS_FILE" "$INSTALLED_REQUIREMENTS_FILE"
fi

# Check if .env exists and has LLM_API_KEY
if [ ! -f "$ENV_FILE" ] || ! grep -q "^LLM_API_KEY=" "$ENV_FILE"; then
    echo -e "${YELLOW}Setting up .env file...${NC}"
    echo -n "Enter your LLM API key: "
    read -r API_KEY
    
    if [ -f "$ENV_FILE" ]; then
        # Update existing .env
        if grep -q "^LLM_API_KEY=" "$ENV_FILE"; then
            # Replace existing key
            sed -i.bak "s/^LLM_API_KEY=.*/LLM_API_KEY=$API_KEY/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
        else
            # Add key
            echo "LLM_API_KEY=$API_KEY" >> "$ENV_FILE"
        fi
    else
        # Create new .env
        echo "LLM_API_KEY=$API_KEY" > "$ENV_FILE"
    fi
fi

# Run main.py
python3 main.py
