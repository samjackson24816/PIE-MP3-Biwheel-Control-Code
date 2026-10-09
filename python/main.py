import time
import threading
import sys
import os
import cv2
import numpy as np
from flask import Flask, Response, jsonify
from arduino.app_utils import App, Bridge

# Ensure import of root vision.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vision import VisionTracker

print("Starting Biwheel Control Python MPU App with Direct-Connection Web Dashboard...")

# Shared thread-safe telemetry and JPEG buffer
state_lock = threading.Lock()
latest_jpeg = None
current_telemetry = {
    "state": "INITIALIZING",
    "x_offset": None,
    "y_offset": None,
    "color": None,
    "area": 0.0,
    "delta": 0.0,
    "left_speed": 0,
    "right_speed": 0,
    "fps": 0.0
}

# Create an initial placeholder image immediately so web stream never blocks
init_img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.putText(init_img, "Camera Initializing...", (140, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
_, enc_init = cv2.imencode('.jpg', init_img)
latest_jpeg = enc_init.tobytes()

app = Flask(__name__)

# Suppress Flask request logging in terminal to keep stdout clean
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            with state_lock:
                frame_bytes = latest_jpeg
            if frame_bytes is None:
                time.sleep(0.05)
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.04)  # ~25 FPS max client transmission
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    with state_lock:
        return jsonify(current_telemetry)

@app.route('/')
def index():
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Biwheel Robot Live Dashboard</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: #1e1e24;
            color: #f0f0f5;
            margin: 0;
            padding: 20px;
        }
        h1 { margin: 0 0 15px 0; font-size: 24px; color: #ffffff; text-align: center; }
        .dashboard {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: #2a2a35;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .video-card { flex: 1 1 640px; max-width: 680px; text-align: center; }
        .telemetry-card { flex: 1 1 360px; max-width: 440px; }
        img {
            width: 100%;
            height: auto;
            border-radius: 6px;
            background: #111;
            display: block;
        }
        .state-banner {
            font-size: 20px;
            font-weight: bold;
            padding: 12px;
            border-radius: 6px;
            text-align: center;
            margin-bottom: 16px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        .state-scan { background-color: #d35400; color: #fff; }
        .state-hunt { background-color: #27ae60; color: #fff; }
        .state-init { background-color: #7f8c8d; color: #fff; }
        .metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .metric-box {
            background: #1c1c24;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }
        .metric-label { font-size: 11px; text-transform: uppercase; color: #8a8aa0; margin-bottom: 4px; }
        .metric-value { font-size: 18px; font-weight: bold; color: #ffffff; }
        .motors-box {
            grid-column: span 2;
            background: #1c1c24;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #9b59b6;
        }
        .motor-bars {
            display: flex;
            gap: 16px;
            margin-top: 8px;
        }
        .motor-col { flex: 1; text-align: center; font-size: 14px; }
    </style>
</head>
<body>
    <h1>Arduino UNO Q Biwheel Robot Live Dashboard</h1>
    <div class="dashboard">
        <div class="card video-card">
            <img src="/video_feed" alt="Live Camera Feed">
        </div>
        <div class="card telemetry-card">
            <div id="state-banner" class="state-banner state-init">INITIALIZING</div>
            <div class="metric-grid">
                <div class="metric-box">
                    <div class="metric-label">X Offset (x_norm)</div>
                    <div id="val-x" class="metric-value">0.00</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Steering Delta</div>
                    <div id="val-delta" class="metric-value">0.00&deg;</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Detected Target</div>
                    <div id="val-color" class="metric-value">None</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Target Area</div>
                    <div id="val-area" class="metric-value">0 px</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Vision FPS</div>
                    <div id="val-fps" class="metric-value">0.0</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Y Offset (y_norm)</div>
                    <div id="val-y" class="metric-value">0.00</div>
                </div>
                <div class="motors-box">
                    <div class="metric-label">Motor Speeds (PWM / Direction)</div>
                    <div class="motor-bars">
                        <div class="motor-col">
                            <strong>Left Motor</strong>
                            <div id="val-motor-l" style="font-size: 18px; color: #2ecc71;">0</div>
                        </div>
                        <div class="motor-col">
                            <strong>Right Motor</strong>
                            <div id="val-motor-r" style="font-size: 18px; color: #2ecc71;">0</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function updateTelemetry() {
            try {
                const res = await fetch('/status');
                if (!res.ok) return;
                const d = await res.json();

                const banner = document.getElementById('state-banner');
                if (d.state === 'HUNT') {
                    banner.innerText = 'HUNTING TARGET';
                    banner.className = 'state-banner state-hunt';
                } else if (d.state === 'SCAN') {
                    banner.innerText = 'SCANNING';
                    banner.className = 'state-banner state-scan';
                } else {
                    banner.innerText = d.state;
                    banner.className = 'state-banner state-init';
                }

                document.getElementById('val-x').innerText = d.x_offset !== null ? (d.x_offset > 0 ? '+' : '') + d.x_offset.toFixed(2) : '--';
                document.getElementById('val-y').innerText = d.y_offset !== null ? (d.y_offset > 0 ? '+' : '') + d.y_offset.toFixed(2) : '--';
                document.getElementById('val-delta').innerText = (d.delta > 0 ? '+' : '') + d.delta.toFixed(2) + '°';
                document.getElementById('val-color').innerText = d.color ? d.color : 'None';
                document.getElementById('val-area').innerText = Math.round(d.area) + ' px';
                document.getElementById('val-fps').innerText = d.fps.toFixed(1);
                document.getElementById('val-motor-l').innerText = d.left_speed;
                document.getElementById('val-motor-r').innerText = d.right_speed;
            } catch (err) {}
        }
        setInterval(updateTelemetry, 150);
    </script>
</body>
</html>
"""

def start_flask_server():
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)

# Start Flask server immediately at import time so port 5000 is always alive
flask_thread = threading.Thread(target=start_flask_server, daemon=True)
flask_thread.start()
print("Flask server thread started immediately on port 5000.")

tracker = None
current_state = "SCAN"

def init_vision_and_control():
    global tracker, current_state
    try:
        tracker = VisionTracker()
    except Exception as e:
        print(f"VisionTracker initialization error: {e}")
        tracker = None
    try:
        Bridge.notify("scan")
        print("Initial state sent to Bridge: SCAN")
    except Exception as e:
        print(f"Bridge notify exception: {e}")

SCAN_SPEED = 30
HUNT_BASE_SPEED = 50
last_time = time.time()
frame_count = 0
calculated_fps = 0.0

def step():
    """Executed repeatedly by Arduino App loop."""
    global tracker, current_state, latest_jpeg, current_telemetry
    global last_time, frame_count, calculated_fps

    if tracker is None:
        init_vision_and_control()

    if tracker is None or not getattr(tracker, 'cam', None) or not tracker.cam.isOpened():
        time.sleep(0.5)
        return

    ret, frame = tracker.cam.read()
    if not ret or frame is None:
        time.sleep(0.04)
        return

    frame_count += 1
    now = time.time()
    if now - last_time >= 1.0:
        calculated_fps = frame_count / (now - last_time)
        frame_count = 0
        last_time = now

    # Single pass vision processing & drawing
    x_norm, y_norm, color_name, area, best_box = tracker.process_frame(frame, draw_annotations=True)

    delta = 0.0
    if x_norm is not None and area > 100:
        if current_state != "HUNT":
            print(f"Target found ({color_name}, area={int(area)}) -> Switching to HUNT")
            current_state = "HUNT"

        delta = x_norm * 30.0
        try:
            Bridge.notify("hunt", float(delta))
        except Exception:
            pass

        l_speed = HUNT_BASE_SPEED + int(delta)
        r_speed = HUNT_BASE_SPEED - int(delta)
    else:
        if current_state != "SCAN":
            print("Target lost -> Switching to SCAN")
            current_state = "SCAN"
            try:
                Bridge.notify("scan")
            except Exception:
                pass

        l_speed = SCAN_SPEED
        r_speed = -HUNT_BASE_SPEED

    # Draw telemetry overlay text directly onto frame
    cv2.putText(frame, f"STATE: {current_state} | FPS: {calculated_fps:.1f}", 
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
    if current_state == "HUNT":
        cv2.putText(frame, f"Target: {color_name} | x_norm: {x_norm:+.2f} | delta: {delta:+.1f}", 
                    (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 0), 2)

    ret_enc, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    encoded_bytes = encoded.tobytes() if ret_enc else None

    with state_lock:
        if encoded_bytes is not None:
            latest_jpeg = encoded_bytes
        current_telemetry = {
            "state": current_state,
            "x_offset": x_norm,
            "y_offset": y_norm,
            "color": color_name,
            "area": area,
            "delta": delta,
            "left_speed": l_speed,
            "right_speed": r_speed,
            "fps": calculated_fps
        }

    time.sleep(0.03)

if __name__ == '__main__':
    App.run(user_loop=step)
