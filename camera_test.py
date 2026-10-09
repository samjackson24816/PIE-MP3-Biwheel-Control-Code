from flask import Flask, Response, jsonify
import time
import os
import sys

# When running camera_test.py standalone, import and delegate to the unified pipeline
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from vision import VisionTracker

# Redirect note
if __name__ == '__main__':
    print("NOTE: python/main.py is the primary unified app running both robot control and the web server.")
    print("To test camera alone, use python/main.py or run restart_camera.sh.")
