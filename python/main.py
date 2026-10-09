import time
import threading
import json
import cv2
import numpy as np
from flask import Flask, Response, jsonify
from arduino.app_utils import App, Bridge
from vision import VisionTracker

print("Starting Biwheel Control Python MPU App with Vision Tracking & Telemetry Stream Server...")

# Shared state & telemetry
latest_frame = None
frame_lock = threading.Lock()
telemetry_lock = threading.Lock()

current_telemetry = {
    "state": "SCAN",
    "x_offset": None,
    "color": None,
    "area": 0.0,
    "delta": 0.0,
    "left_speed": 0,
    "right_speed": 0
}

app = Flask(__name__)

@app.route('/video_feed')
def video_feed():
    def generate():
        global latest_frame
        while True:
            with frame_lock:
                if latest_frame is None:
                    # Create a placeholder frame so stream never hangs
                    placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "Camera Initializing...", (160, 240), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                    frame_to_encode = placeholder
                else:
                    frame_to_encode = latest_frame
                
                success, encoded = cv2.imencode('.jpg', frame_to_encode)
                if not success:
                    time.sleep(0.05)
                    continue
                frame_bytes = encoded.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.05)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    with telemetry_lock:
        return jsonify(current_telemetry)

@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Biwheel Robot Telemetry & Live Stream</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f9; color: #333; text-align: center; margin: 0; padding: 20px; }
        h1 { color: #2c3e50; }
        .container { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px; }
        .video-box, .telemetry-box { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        img { max-width: 100%; height: auto; border: 2px solid #bdc3c7; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; border-bottom: 1px solid #ddd; text-align: left; }
        th { background-color: #2980b9; color: white; }
        .badge { padding: 5px 10px; border-radius: 4px; font-weight: bold; color: white; }
        .badge-scan { background-color: #e67e22; }
        .badge-hunt { background-color: #27ae60; }
    </style>
</head>
<body>
    <h1>Arduino UNO Q Biwheel Robot Dashboard</h1>
    <div class="container">
        <div class="video-box">
            <h3>Live Camera Stream</h3>
            <img src="/video_feed" width="640" height="480">
        </div>
        <div class="telemetry-box">
            <h3>Real-Time Telemetry</h3>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>State</td><td><span id="state" class="badge">SCAN</span></td></tr>
                <tr><td>X Offset (x_norm)</td><td id="x_offset">0.00</td></tr>
                <tr><td>Detected Color</td><td id="color">None</td></tr>
                <tr><td>Shape Area</td><td id="area">0.0</td></tr>
                <tr><td>Steering Delta</td><td id="delta">0.0</td></tr>
                <tr><td>Est. Motor Speeds (L / R)</td><td id="motors">L: 0, R: 0</td></tr>
            </table>
        </div>
    </div>

    <script>
        setInterval(async () => {
            try {
                let res = await fetch('/status');
                let data = await res.json();
                
                let stateSpan = document.getElementById('state');
                stateSpan.innerText = data.state;
                stateSpan.className = "badge " + (data.state === "HUNT" ? "badge-hunt" : "badge-scan");
                
                document.getElementById('x_offset').innerText = data.x_offset !== null ? data.x_offset.toFixed(3) : "None";
                document.getElementById('color').innerText = data.color || "None";
                document.getElementById('area').innerText = data.area.toFixed(1);
                document.getElementById('delta').innerText = data.delta.toFixed(2);
                document.getElementById('motors').innerText = `L: ${data.left_speed}, R: ${data.right_speed}`;
            } catch (e) {
                console.error("Error fetching telemetry:", e);
            }
        }, 200);
    </script>
</body>
</html>
    """

def start_flask_server():
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)

def run_vision_and_control():
    global latest_frame, current_telemetry
    print("=== PART 2 VISION TRACKING & HUNTING START ===")
    tracker = VisionTracker()
    
    current_state = "SCAN"
    print("State: SCAN (turning slowly in circles)")
    Bridge.notify("scan")
    
    scan_left_speed = 30
    scan_right_speed = -50
    hunt_base_speed = 50

    try:
        while True:
            ret, frame = tracker.cam.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue
            
            # Update shared frame for Flask web server
            with frame_lock:
                latest_frame = frame.copy()
            
            # Run vision processing on the frame
            x_norm, y_norm, color_name, area = tracker.get_largest_shape_position_from_frame(frame)
            
            delta = 0.0
            l_speed = scan_left_speed
            r_speed = scan_right_speed

            # Check if an item is detected (area > 100)
            if x_norm is not None and area > 100:
                if current_state != "HUNT":
                    print(f"Item detected ({color_name}, area={area:.1f})! Switching to HUNT mode.")
                    current_state = "HUNT"
                
                # Calculate steering delta from x_norm (-1 to 1)
                delta = x_norm * 30.0
                Bridge.notify("hunt", float(delta))
                
                # Estimate motor speeds matching STM32 sketch logic
                l_speed = hunt_base_speed + int(delta)
                r_speed = hunt_base_speed - int(delta)
            else:
                if current_state != "SCAN":
                    print("Lost item / No item in frame. Switching back to SCAN mode.")
                    current_state = "SCAN"
                    Bridge.notify("scan")
                l_speed = scan_left_speed
                r_speed = scan_right_speed

            # Update telemetry for dashboard
            with telemetry_lock:
                current_telemetry = {
                    "state": current_state,
                    "x_offset": x_norm,
                    "color": color_name,
                    "area": area,
                    "delta": delta,
                    "left_speed": l_speed,
                    "right_speed": r_speed
                }
            
            time.sleep(0.05)
            
    except Exception as e:
        print(f"Error in vision loop: {e}")
    finally:
        tracker.release()
        Bridge.notify("stop")

def loop():
    # Start Flask server in background thread once
    flask_thread = threading.Thread(target=start_flask_server, daemon=True)
    flask_thread.start()
    print("Flask video streaming server & telemetry dashboard started on port 5000")
    
    # Run vision and robot control sequence
    run_vision_and_control()
    
    while True:
        time.sleep(60)

App.run(user_loop=loop)
