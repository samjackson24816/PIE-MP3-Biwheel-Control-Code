#!/bin/bash
set -e

echo "=== Setting up System Dependencies ==="
sudo apt update
sudo apt install -y python3-flask python3-opencv v4l-utils python3-pip

echo "=== Ensuring requirements.txt files exist ==="
cat << 'EOF' > requirements.txt
flask
opencv-python-headless
numpy
EOF

cat << 'EOF' > python/requirements.txt
flask
opencv-python-headless
numpy
EOF

echo "=== Setup complete! ==="
echo "You can now run: arduino-app-cli app restart ."
