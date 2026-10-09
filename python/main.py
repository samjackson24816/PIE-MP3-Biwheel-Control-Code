import time
import sys
import os
import json
import cv2
from arduino.app_utils import App, Bridge

# Ensure import of root vision.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vision import VisionTracker
from display import DisplayManager

print("Starting Biwheel Control Python MPU App with Direct-Connection Web Dashboard...")

# Config file path for persistent settings
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.json'))

# Hardcoded system defaults
DEFAULT_CONFIG = {
    "scan_speed": 30,
    "hunt_base_speed": 50,
    "min_area": 100,
    "min_sat": 120,
    "min_val": 80,
    "hue_tolerance": 10
}

def load_config():
    """Loads configuration from config.json, creating it with defaults if missing."""
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg.update(loaded)
            print(f"Loaded persistent config from {CONFIG_FILE}: {cfg}")
        except Exception as e:
            print(f"Error loading {CONFIG_FILE}, using defaults: {e}")
    else:
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(cfg, f, indent=2)
            print(f"Created default config file at {CONFIG_FILE}")
        except Exception as e:
            print(f"Could not create config file: {e}")
    return cfg

def save_config_file(cfg):
    """Writes configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
        print(f"Saved configuration to {CONFIG_FILE}: {cfg}")
        return True
    except Exception as e:
        print(f"Failed to save config to {CONFIG_FILE}: {e}")
        return False

# Initialize settings from file on startup
active_config = load_config()
scan_speed = int(active_config["scan_speed"])
hunt_base_speed = int(active_config["hunt_base_speed"])
min_area = int(active_config["min_area"])
min_sat = int(active_config["min_sat"])
min_val = int(active_config["min_val"])
hue_tolerance = int(active_config["hue_tolerance"])

tracker = None
current_state = "SCAN"

def on_speed_change_callback(data):
    """Callback triggered when settings are modified via web dashboard."""
    global scan_speed, hunt_base_speed, min_area, min_sat, min_val, hue_tolerance, tracker
    if 'scan_speed' in data:
        scan_speed = max(0, min(255, int(data['scan_speed'])))
    if 'hunt_base_speed' in data:
        hunt_base_speed = max(0, min(255, int(data['hunt_base_speed'])))
    if 'min_area' in data:
        min_area = max(1, min(5000, int(data['min_area'])))
    if 'min_sat' in data:
        min_sat = max(0, min(255, int(data['min_sat'])))
    if 'min_val' in data:
        min_val = max(0, min(255, int(data['min_val'])))
    if 'hue_tolerance' in data:
        hue_tolerance = max(1, min(45, int(data['hue_tolerance'])))

    if tracker is not None:
        tracker.set_parameters(
            min_area=min_area,
            min_sat=min_sat,
            min_val=min_val,
            hue_tolerance=hue_tolerance
        )

    return {
        "scan_speed": scan_speed,
        "hunt_base_speed": hunt_base_speed,
        "min_area": min_area,
        "min_sat": min_sat,
        "min_val": min_val,
        "hue_tolerance": hue_tolerance
    }

def on_save_config_callback():
    """Callback triggered when saving settings to disk via web dashboard."""
    cfg = {
        "scan_speed": scan_speed,
        "hunt_base_speed": hunt_base_speed,
        "min_area": min_area,
        "min_sat": min_sat,
        "min_val": min_val,
        "hue_tolerance": hue_tolerance
    }
    success = save_config_file(cfg)
    return success, cfg

# Start display manager and web server immediately on port 5000
display_mgr = DisplayManager(
    host='0.0.0.0',
    port=5000,
    initial_config=active_config,
    on_speed_change=on_speed_change_callback,
    on_save_config=on_save_config_callback
)
display_mgr.start()

def send_motors(l_speed, r_speed):
    """Sends raw target speeds to STM32 via set_motors, falling back to legacy methods if needed."""
    try:
        Bridge.notify("set_motors", int(l_speed), int(r_speed))
    except Exception as e:
        # Fallback if set_motors is not yet flashed on the Arduino
        try:
            if l_speed == scan_speed and r_speed == -scan_speed:
                Bridge.notify("scan")
            else:
                Bridge.notify("hunt", float(l_speed - hunt_base_speed))
        except Exception:
            pass

def init_vision_and_control():
    global tracker, current_state
    try:
        tracker = VisionTracker(
            min_area=min_area,
            min_sat=min_sat,
            min_val=min_val,
            hue_tolerance=hue_tolerance
        )
    except Exception as e:
        print(f"VisionTracker initialization error: {e}")
        tracker = None
    try:
        send_motors(scan_speed, -scan_speed)
        print("Initial state sent to Bridge: SCAN")
    except Exception as e:
        print(f"Bridge notify exception: {e}")

last_time = time.time()
frame_count = 0
calculated_fps = 0.0

def step():
    """Executed repeatedly by Arduino App loop."""
    global tracker, current_state
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
    if best_box is not None and x_norm is not None:
        if current_state != "HUNT":
            print(f"Target found ({color_name}, area={int(area)}) -> Switching to HUNT")
            current_state = "HUNT"

        delta = x_norm * 30.0
        l_speed = int(hunt_base_speed + delta)
        r_speed = int(hunt_base_speed - delta)
        send_motors(l_speed, r_speed)
    else:
        if current_state != "SCAN":
            print("Target lost -> Switching to SCAN")
            current_state = "SCAN"

        l_speed = int(scan_speed)
        r_speed = int(-scan_speed)
        send_motors(l_speed, r_speed)

    # Draw telemetry overlay text directly onto frame
    display_mgr.draw_telemetry_overlay(
        frame=frame,
        state=current_state,
        fps=calculated_fps,
        color_name=color_name,
        x_norm=x_norm,
        delta=delta
    )

    # Update web display with new frame and telemetry values
    display_mgr.update_frame_and_telemetry(
        frame=frame,
        telemetry_dict={
            "state": current_state,
            "x_offset": x_norm,
            "y_offset": y_norm,
            "color": color_name,
            "area": area,
            "delta": delta,
            "left_speed": l_speed,
            "right_speed": r_speed,
            "fps": calculated_fps,
            "scan_speed": scan_speed,
            "hunt_base_speed": hunt_base_speed,
            "min_area": min_area,
            "min_sat": min_sat,
            "min_val": min_val,
            "hue_tolerance": hue_tolerance
        }
    )

    time.sleep(0.03)

if __name__ == '__main__':
    App.run(user_loop=step)
