import cv2
import numpy as np

class VisionTracker:
    def __init__(self, camera_index=0):
        """Initializes webcam capture with fallback from index 0 to 1."""
        self.cam = cv2.VideoCapture(camera_index)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not self.cam.isOpened():
            print(f"WARNING: Camera index {camera_index} failed to open. Trying index 1...")
            self.cam = cv2.VideoCapture(1)
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
        if self.cam.isOpened():
            print("SUCCESS: Camera opened successfully.")
        else:
            print("ERROR: Could not open camera at index 0 or 1.")

    def process_frame(self, frame, draw_annotations=True):
        """
        Runs color segmentation and shape detection in a single pass.
        Optionally annotates the frame in-place with bounding boxes, center crosshairs,
        and target labels so that downstream visualization requires zero extra compute.

        Returns:
            tuple: (x_norm, y_norm, color_name, area, best_box)
                   where best_box is (x, y, w, h) or None
        """
        if frame is None:
            return None, None, None, 0.0, None

        h, w = frame.shape[:2]
        cx, cy = w / 2.0, h / 2.0

        hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Red color ranges
        red_lower1 = np.array([0, 120, 80], np.uint8)
        red_upper1 = np.array([10, 255, 255], np.uint8)
        red_lower2 = np.array([170, 120, 80], np.uint8)
        red_upper2 = np.array([180, 255, 255], np.uint8)

        # Green color range
        green_lower = np.array([25, 52, 72], np.uint8)
        green_upper = np.array([102, 255, 255], np.uint8)

        # Blue color range
        blue_lower = np.array([94, 80, 2], np.uint8)
        blue_upper = np.array([120, 255, 255], np.uint8)

        red_mask1 = cv2.inRange(hsvFrame, red_lower1, red_upper1)
        red_mask2 = cv2.inRange(hsvFrame, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

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

        largest_area = 0.0
        best_box = None
        best_color = None

        for color_name, mask, bgr_color in color_masks:
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:
                    bx, by, bw, bh = cv2.boundingRect(contour)
                    if draw_annotations:
                        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), bgr_color, 2)
                    if area > largest_area:
                        largest_area = float(area)
                        best_box = (bx, by, bw, bh)
                        best_color = color_name

        # Draw crosshair at center (0,0)
        if draw_annotations:
            cross_size = 20
            cv2.line(frame, (int(cx) - cross_size, int(cy)), (int(cx) + cross_size, int(cy)), (0, 255, 255), 2)
            cv2.line(frame, (int(cx), int(cy) - cross_size), (int(cx), int(cy) + cross_size), (0, 255, 255), 2)

        if best_box is not None:
            bx, by, bw, bh = best_box
            center_x = bx + bw / 2.0
            center_y = by + bh / 2.0

            x_norm = (center_x - cx) / cx
            y_norm = (cy - center_y) / cy

            if draw_annotations:
                # Highlight the targeted/largest box with a thicker yellow border and center dot
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 255), 3)
                cv2.circle(frame, (int(center_x), int(center_y)), 5, (0, 255, 255), -1)

            return float(x_norm), float(y_norm), best_color, float(largest_area), best_box

        return None, None, None, 0.0, None

    def get_largest_shape_position_from_frame(self, frame):
        """Backward compatibility helper."""
        x_norm, y_norm, color, area, _ = self.process_frame(frame, draw_annotations=False)
        return x_norm, y_norm, color, area

    def release(self):
        """Releases the webcam resource."""
        if self.cam.isOpened():
            self.cam.release()
