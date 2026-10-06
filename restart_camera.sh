#!/bin/bash
# Stop any existing camera server processes
echo "Stopping existing camera server processes..."
pkill -f camera_test.py

# Start the camera test server persistently using nohup so it survives SSH disconnection
echo "Starting camera_test.py persistently..."
nohup python3 camera_test.py > camera_server.log 2>&1 &
disown

echo "Camera server is now running persistently in the background!"
echo "Logs are saved to camera_server.log"
echo "Access the live stream at http://<board-ip>:5000"
