#!/bin/bash
# Quick start script for Trading Terminal

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate virtual environment
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
else
    echo "Error: Virtual environment not found at $PARENT_DIR/.venv"
        echo "Please create it with: python3 -m venv .venv"                
        exit 1                                                             
    fi                                                                     
                                                                            
    # Change to trading-terminal directory and run
    cd "$SCRIPT_DIR"

    # Set Qt plugin path for PyQt6 on macOS
    export QT_PLUGIN_PATH=/opt/anaconda3/lib/python3.13/site-packages/PyQt6/Qt6/plugins

    python3 trading_app.py

