import time
import threading
import cv2
from flask import Flask, Response
from arduino.app_utils import App, Bridge
from vision import VisionTracker

print("Starting Biwheel Control Python MPU App with Vision Tracking & Live Stream Server...")

# Shared state / latest frame for streaming
latest_frame = None
frame_lock = threading.Lock()

app = Flask(__name__)

@app.route('/video_feed')
def video_feed():
    def generate():
        global latest_frame
        while True:
            with frame_lock:
                if latest_frame is None:
                    time.sleep(0.05)
                    continue
                success, encoded = cv2.imencode('.jpg', latest_frame)
                if not success:
                    continue
                frame_bytes = encoded.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.03)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "<h1>Arduino UNO Q Biwheel Robot Live Stream & Vision Tracker</h1><img src='/video_feed'>"

def start_flask_server():
    app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)

def run_vision_and_control():
    global latest_frame
    print("=== PART 2 VISION TRACKING & HUNTING START ===")
    tracker = VisionTracker()
    
    current_state = "SCAN"
    print("State: SCAN (turning slowly in circles)")
    Bridge.notify("scan")
    
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
            
            # Check if an item is detected (area > 100)
            if x_norm is not None and area > 100:
                if current_state != "HUNT":
                    print(f"Item detected ({color_name}, area={area:.1f})! Switching to HUNT mode.")
                    current_state = "HUNT"
                
                # Calculate steering delta from x_norm (-1 to 1)
                delta = x_norm * 30.0
                Bridge.notify("hunt", float(delta))
            else:
                if current_state != "SCAN":
                    print("Lost item / No item in frame. Switching back to SCAN mode.")
                    current_state = "SCAN"
                    Bridge.notify("scan")
            
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
    print("Flask video streaming server started on port 5000")
    
    # Run vision and robot control sequence
    run_vision_and_control()
    
    while True:
        time.sleep(60)

App.run(user_loop=loop)
