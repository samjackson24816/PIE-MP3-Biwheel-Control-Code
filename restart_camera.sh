#!/bin/bash
# Stop any existing camera test or flask servers running on port 5000
echo "Stopping existing servers on port 5000..."
fuser -k 5000/tcp 2>/dev/null || true
pkill -f camera_test.py 2>/dev/null || true

# Restart the Arduino App which runs python/main.py
echo "Restarting Arduino App (PIE-MP3-Biwheel-Control-Code)..."
arduino-app-cli app restart PIE-MP3-Biwheel-Control-Code

echo "Arduino App restarted! python/main.py is running the live dashboard and vision control."
echo "Access the live stream & telemetry dashboard at http://<board-ip>:5000"
