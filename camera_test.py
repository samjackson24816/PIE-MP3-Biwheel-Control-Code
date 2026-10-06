from flask import Flask, Response
import cv2
import numpy as np
import time
from vision import VisionTracker

app = Flask(__name__)
tracker = VisionTracker(camera_index=0)

def generate_frames():
    while True:
        if not tracker.cam.isOpened():
            break
        success, frame = tracker.cam.read()
        if not success or frame is None:
            time.sleep(0.1)
            continue
        
        h, w = frame.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        
        font_scale = max(0.8, h / 450.0)
        thickness = max(2, int(h / 200.0))
        
        hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        red_lower1 = np.array([0, 120, 80], np.uint8)
        red_upper1 = np.array([10, 255, 255], np.uint8)
        red_lower2 = np.array([170, 120, 80], np.uint8)
        red_upper2 = np.array([180, 255, 255], np.uint8)
        green_lower = np.array([25, 52, 72], np.uint8)
        green_upper = np.array([102, 255, 255], np.uint8)
        blue_lower = np.array([94, 80, 2], np.uint8)
        blue_upper = np.array([120, 255, 255], np.uint8)
        
        red_mask = cv2.bitwise_or(cv2.inRange(hsvFrame, red_lower1, red_upper1), cv2.inRange(hsvFrame, red_lower2, red_upper2))
        green_mask = cv2.inRange(hsvFrame, green_lower, green_upper)
        blue_mask = cv2.inRange(hsvFrame, blue_lower, blue_upper)
        
        kernel = np.ones((5, 5), "uint8")
        red_mask = cv2.dilate(red_mask, kernel)
        green_mask = cv2.dilate(green_mask, kernel)
        blue_mask = cv2.dilate(blue_mask, kernel)
        
        color_masks = [
            ("Red", red_mask, (0, 0, 255)),
            ("Green", green_mask, (0, 255, 0)),
            ("Blue", blue_mask, (255, 0, 0))
        ]
        
        for color_name, mask, bgr in color_masks:
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                if cv2.contourArea(contour) > 100:
                    x, y, w_box, h_box = cv2.boundingRect(contour)
                    cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), bgr, thickness)

        # Draw crosshair at center (0,0)
        cross_size = 20
        cv2.line(frame, (int(cx) - cross_size, int(cy)), (int(cx) + cross_size, int(cy)), (0, 255, 255), thickness)
        cv2.line(frame, (int(cx), int(cy) - cross_size), (int(cx), int(cy) + cross_size), (0, 255, 255), thickness)

        x_norm, y_norm, color, area = tracker.get_largest_shape_position_from_frame(frame)
        
        if x_norm is not None and y_norm is not None:
            info_text = f"Largest: {color} | X: {x_norm:+.2f}, Y: {y_norm:+.2f} | Area: {int(area)}"
            cv2.putText(frame, info_text, (30, 45), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness)
        else:
            cv2.putText(frame, "Status: Searching for shapes...", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 165, 255), thickness)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "<h1>Arduino UNO Q Camera Live Stream with VisionTracker</h1><img src='/video_feed'>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
