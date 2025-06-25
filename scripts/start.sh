#!/bin/bash
# LLM Chat System - Unix/Linux Startup Script

set -e

echo ""
echo "========================================"
echo "  LLM Chat System - Unix/Linux Launcher"
echo "========================================"
echo ""

# Change to project directory
cd "$(dirname "$0")/.."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Use python3 explicitly
PYTHON_CMD="python3"

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
REQUIRED_VERSION="3.8"

if ! $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "Error: Python $PYTHON_VERSION is installed, but Python $REQUIRED_VERSION or higher is required"
    exit 1
fi

# Check if virtual environment exists and activate it
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    PYTHON_CMD="python"
fi

# Check if requirements are installed
if ! $PYTHON_CMD -c "import openai" &> /dev/null; then
    echo "Installing requirements..."
    $PYTHON_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install requirements"
        exit 1
    fi
fi

# Initialize system if needed
if [ ! -f "config/default_config.json" ]; then
    echo "Initializing system..."
    $PYTHON_CMD scripts/init.py
    if [ $? -ne 0 ]; then
        echo "Error: System initialization failed"
        exit 1
    fi
fi

# Start the system
echo "Starting LLM Chat System..."
$PYTHON_CMD scripts/start.py "$@"
