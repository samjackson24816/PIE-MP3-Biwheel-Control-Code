#!/bin/bash
# Free port 5000 in case a stale process is holding it
echo "Freeing port 5000..."
fuser -k 5000/tcp 2>/dev/null || true

# Check if arduino-app-cli is available
if command -v arduino-app-cli &> /dev/null; then
    echo "Restarting Arduino App via arduino-app-cli..."
    arduino-app-cli app restart . 2>/dev/null || arduino-app-cli app start .
    echo "App started! Following live logs (Ctrl+C to exit log view):"
    arduino-app-cli app logs . --follow
else
    # Fallback to direct python if venv or python path is used
    echo "Running with python3..."
    python3 python/main.py
fi
