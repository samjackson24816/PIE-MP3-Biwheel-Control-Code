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

    def get_largest_shape_position_from_frame(self, frame):
        """
        Analyzes a given frame, detects red, green, and blue shapes,
        finds the largest shape overall, and returns its normalized position (x, y)
        where:
          - (0, 0) is the center of the frame
          - Upper right corner is (1, 1)
          - X ranges from -1 (left) to +1 (right)
          - Y ranges from -1 (bottom) to +1 (top)

        Returns:
            tuple: (x_norm, y_norm, color_name, area) if a shape is found,
                   otherwise (None, None, None, 0.0)
        """
        if frame is None:
            return None, None, None, 0.0

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
            ("Red", red_mask),
            ("Green", green_mask),
            ("Blue", blue_mask)
        ]

        largest_area = 0
        best_contour = None
        best_color = None

        for color_name, mask in color_masks:
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100 and area > largest_area:
                    largest_area = area
                    best_contour = contour
                    best_color = color_name

        if best_contour is not None:
            x, y, w_box, h_box = cv2.boundingRect(best_contour)
            center_x = x + w_box / 2.0
            center_y = y + h_box / 2.0

            x_norm = (center_x - cx) / cx
            y_norm = (cy - center_y) / cy

            return float(x_norm), float(y_norm), best_color, float(largest_area)

        return None, None, None, 0.0

    def get_largest_shape_position(self):
        """Captures a frame and returns the largest shape normalized position."""
        if not self.cam.isOpened():
            return None, None, None, 0.0
        ret, frame = self.cam.read()
        if not ret or frame is None:
            return None, None, None, 0.0
        return self.get_largest_shape_position_from_frame(frame)

    def release(self):
        """Releases the webcam resource."""
        if self.cam.isOpened():
            self.cam.release()
