#!/bin/bash
# Stop any stale Python or Flask process bound to port 5000
echo "Freeing port 5000..."
fuser -k 5000/tcp 2>/dev/null || true
pkill -f camera_test.py 2>/dev/null || true

# Run python/main.py directly with python3
echo "Starting python/main.py directly..."
cd "$(dirname "$0")"
python3 python/main.py
