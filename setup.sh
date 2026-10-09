#!/bin/bash
set -e

echo "=== Setting up System Dependencies ==="
sudo apt update
sudo apt install -y python3-flask python3-opencv v4l-utils

echo "=== Ensuring requirements.txt files exist ==="
echo "flask" > requirements.txt
echo "flask" > python/requirements.txt

echo "=== Setup complete! ==="
echo "You can now run: ./run.sh"
