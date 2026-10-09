import time
import os
import cv2
import numpy as np
from flask import Flask, Response, jsonify, request, render_template
import threading
import logging

class DisplayManager:
    """Manages web dashboard, telemetry overlays, and MJPEG video streaming."""

    def __init__(self, host='0.0.0.0', port=5000, initial_config=None, on_speed_change=None, on_save_config=None):
        self.host = host
        self.port = port
        self.on_speed_change = on_speed_change
        self.on_save_config = on_save_config

        self.lock = threading.Lock()
        self.latest_jpeg = None
        self.last_encode_time = 0.0
        # Throttle display encoding to ~10 FPS (100ms) to ensure consistent, low CPU usage
        self.encode_interval = 0.10

        # Display FPS calculation
        self.display_frame_count = 0
        self.display_last_time = time.time()
        self.calculated_display_fps = 0.0

        cfg = initial_config or {}
        self.telemetry = {
            "state": "INITIALIZING",
            "x_offset": None,
            "y_offset": None,
            "color": None,
            "area": 0.0,
            "delta": 0.0,
            "left_speed": 0,
            "right_speed": 0,
            "fps": 0.0,
            "display_fps": 0.0,
            "scan_speed": cfg.get("scan_speed", 30),
            "hunt_base_speed": cfg.get("hunt_base_speed", 50),
            "min_area": cfg.get("min_area", 100),
            "min_sat": cfg.get("min_sat", 120),
            "min_val": cfg.get("min_val", 80),
            "hue_tolerance": cfg.get("hue_tolerance", 10)
        }

        # Placeholder frame so stream responds immediately on boot
        init_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(init_img, "Camera Initializing...", (140, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        _, enc_init = cv2.imencode('.jpg', init_img)
        self.latest_jpeg = enc_init.tobytes()

        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.app = Flask(__name__, template_folder=template_dir)
        self._setup_routes()

        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        self._thread = None

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/video_feed')
        def video_feed():
            def generate():
                while True:
                    with self.lock:
                        frame_bytes = self.latest_jpeg
                    if frame_bytes is None:
                        time.sleep(0.05)
                        continue
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    time.sleep(0.10)  # Stream client transmission matched to ~10 FPS display rate
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

        @self.app.route('/status')
        def status():
            with self.lock:
                return jsonify(self.telemetry)

        @self.app.route('/set_speeds', methods=['POST'])
        def set_speeds():
            data = request.get_json(silent=True) or {}
            updated = {}
            if self.on_speed_change:
                updated = self.on_speed_change(data) or {}

            with self.lock:
                for k in ['scan_speed', 'hunt_base_speed', 'min_area', 'min_sat', 'min_val', 'hue_tolerance']:
                    if k in updated:
                        self.telemetry[k] = updated[k]

            res = {"success": True}
            res.update(updated)
            return jsonify(res)

        @self.app.route('/save_config', methods=['POST'])
        def save_config():
            if self.on_save_config:
                success, cfg = self.on_save_config()
                return jsonify({"success": success, "config": cfg})
            return jsonify({"success": False, "config": {}})

    def draw_telemetry_overlay(self, frame, state, fps, display_fps=0.0, color_name=None, x_norm=None, delta=None):
        """Draws telemetry overlay text directly onto the video frame."""
        cv2.putText(frame, f"STATE: {state} | LOGIC: {fps:.1f} FPS | DISP: {display_fps:.1f} FPS", 
                    (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 255), 2)
        if state == "HUNT" and color_name is not None and x_norm is not None and delta is not None:
            cv2.putText(frame, f"Target: {color_name} | x_norm: {x_norm:+.2f} | delta: {delta:+.1f}", 
                        (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 0), 2)

    def update_frame_and_telemetry(self, frame, telemetry_dict):
        """Encodes frame at throttled display FPS and lower quality, maintaining deterministic behavior."""
        now = time.time()
        encoded_bytes = None

        # Track display encoding FPS
        if frame is not None and (now - self.last_encode_time >= self.encode_interval):
            self.last_encode_time = now
            self.display_frame_count += 1
            ret_enc, encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 40])
            if ret_enc:
                encoded_bytes = encoded.tobytes()

        # Update display FPS measurement once per second
        if now - self.display_last_time >= 1.0:
            self.calculated_display_fps = self.display_frame_count / (now - self.display_last_time)
            self.display_frame_count = 0
            self.display_last_time = now

        with self.lock:
            if encoded_bytes is not None:
                self.latest_jpeg = encoded_bytes
            if telemetry_dict:
                self.telemetry.update(telemetry_dict)
            self.telemetry["display_fps"] = self.calculated_display_fps

    def start(self):
        """Starts the Flask server thread."""
        if self._thread is None:
            self._thread = threading.Thread(
                target=lambda: self.app.run(host=self.host, port=self.port, threaded=True, use_reloader=False),
                daemon=True
            )
            self._thread.start()
            print(f"Display / Flask server thread started immediately on port {self.port}.")
