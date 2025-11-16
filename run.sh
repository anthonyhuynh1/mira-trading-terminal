#!/bin/bash
# Quick start script for Trading Terminal

cd "$(dirname "$0")/.."
source .venv/bin/activate
cd trading-terminal
python trading_app.py

