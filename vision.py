import cv2
import numpy as np

class VisionTracker:
    def __init__(self, camera_index=0, min_area=100, min_sat=120, min_val=80, hue_tolerance=10):
        """Initializes webcam capture with fallback from index 0 to 1."""
        self.cam = cv2.VideoCapture(camera_index)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Vision tuning parameters (default to original values)
        self.min_area = int(min_area)
        self.min_sat = int(min_sat)
        self.min_val = int(min_val)
        self.hue_tolerance = int(hue_tolerance)

        # Pre-allocate morphological kernel and HSV threshold arrays
        self.kernel = np.ones((5, 5), dtype=np.uint8)
        self._update_hsv_ranges()
        
        if not self.cam.isOpened():
            print(f"WARNING: Camera index {camera_index} failed to open. Trying index 1...")
            self.cam = cv2.VideoCapture(1)
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
        if self.cam.isOpened():
            print("SUCCESS: Camera opened successfully.")
        else:
            print("ERROR: Could not open camera at index 0 or 1.")

    def _update_hsv_ranges(self):
        """Pre-computes NumPy arrays for red HSV boundaries to eliminate per-frame allocations."""
        self.red_lower1 = np.array([0, self.min_sat, self.min_val], dtype=np.uint8)
        self.red_upper1 = np.array([self.hue_tolerance, 255, 255], dtype=np.uint8)
        self.red_lower2 = np.array([180 - self.hue_tolerance, self.min_sat, self.min_val], dtype=np.uint8)
        self.red_upper2 = np.array([180, 255, 255], dtype=np.uint8)

    def set_parameters(self, min_area=None, min_sat=None, min_val=None, hue_tolerance=None):
        """Live updates detection thresholds."""
        changed = False
        if min_area is not None:
            self.min_area = max(1, int(min_area))
        if min_sat is not None:
            self.min_sat = max(0, min(255, int(min_sat)))
            changed = True
        if min_val is not None:
            self.min_val = max(0, min(255, int(min_val)))
            changed = True
        if hue_tolerance is not None:
            self.hue_tolerance = max(1, min(45, int(hue_tolerance)))
            changed = True
        if changed:
            self._update_hsv_ranges()

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

        # Downsample 2x for fast segmentation on embedded MPU (QRB2210)
        proc_w, proc_h = w // 2, h // 2
        small_frame = cv2.resize(frame, (proc_w, proc_h), interpolation=cv2.INTER_NEAREST)
        hsvFrame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2HSV)

        # Red color ranges in HSV using pre-allocated threshold arrays
        red_mask1 = cv2.inRange(hsvFrame, self.red_lower1, self.red_upper1)
        red_mask2 = cv2.inRange(hsvFrame, self.red_lower2, self.red_upper2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)

        red_mask = cv2.dilate(red_mask, self.kernel)

        color_masks = [
            ("Red", red_mask, (0, 0, 255)),
        ]

        largest_area = 0.0
        best_box = None
        best_color = None

        # Scale min_area threshold for the downscaled (2x) resolution
        scaled_min_area = self.min_area / 4.0

        for color_name, mask, bgr_color in color_masks:
            # RETR_EXTERNAL avoids computing unnecessary nested contour hierarchies
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > scaled_min_area:
                    bx, by, bw, bh = cv2.boundingRect(contour)
                    # Scale bounding box back to original frame dimensions
                    orig_bx, orig_by = bx * 2, by * 2
                    orig_bw, orig_bh = bw * 2, bh * 2
                    orig_area = float(area * 4.0)

                    if draw_annotations:
                        cv2.rectangle(frame, (orig_bx, orig_by), (orig_bx + orig_bw, orig_by + orig_bh), bgr_color, 2)
                    if orig_area > largest_area:
                        largest_area = orig_area
                        best_box = (orig_bx, orig_by, orig_bw, orig_bh)
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
