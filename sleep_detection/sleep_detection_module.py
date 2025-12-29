"""
Sleep Detection Module
Detects drowsiness and sleepiness from facial features (eye closure, head position)
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import dlib
import os


class SleepDetection:
    """Sleep and drowsiness detection from facial features"""
    
    def __init__(self, predictor_path: str = None):
        """
        Initialize sleep detection system
        
        Args:
            predictor_path: Path to dlib shape predictor (optional)
        """
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        self.predictor = None
        self.detector = None
        
        # Eye aspect ratio threshold (below this indicates closed eyes)
        self.EAR_THRESHOLD = 0.25
        self.EAR_CONSECUTIVE_FRAMES = 3
        
        # Track eye closure frames
        self.eye_closure_counter = {}
        self.eye_closure_history = {}
        
        # Initialize dlib if predictor is provided
        if predictor_path and os.path.exists(predictor_path):
            self.detector = dlib.get_frontal_face_detector()
            self.predictor = dlib.shape_predictor(predictor_path)
    
    def calculate_eye_aspect_ratio(self, eye_points: np.ndarray) -> float:
        """
        Calculate Eye Aspect Ratio (EAR)
        
        Args:
            eye_points: Array of eye landmark points
            
        Returns:
            Eye aspect ratio value
        """
        # Vertical distances
        vertical_1 = np.linalg.norm(eye_points[1] - eye_points[5])
        vertical_2 = np.linalg.norm(eye_points[2] - eye_points[4])
        
        # Horizontal distance
        horizontal = np.linalg.norm(eye_points[0] - eye_points[3])
        
        # Calculate EAR
        if horizontal == 0:
            return 0.0
        
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return ear
    
    def detect_eyes_opencv(self, frame: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Dict:
        """
        Detect eyes using OpenCV
        
        Args:
            frame: Input frame
            face_bbox: Face bounding box (x, y, w, h)
            
        Returns:
            Dictionary with eye detection results
        """
        x, y, w, h = face_bbox
        roi_gray = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 3)
        
        eye_count = len(eyes)
        eyes_open = eye_count >= 2
        
        return {
            'eyes_detected': eye_count,
            'eyes_open': eyes_open,
            'eye_boxes': [(x+ex, y+ey, ew, eh) for (ex, ey, ew, eh) in eyes]
        }
    
    def detect_eyes_dlib(self, frame: np.ndarray, face_bbox: Tuple) -> Dict:
        """
        Detect eyes using dlib landmarks (more accurate)
        
        Args:
            frame: Input frame
            face_bbox: Face bounding box from dlib
            
        Returns:
            Dictionary with eye detection results
        """
        if not self.predictor:
            return self.detect_eyes_opencv(frame, face_bbox)
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        shape = self.predictor(gray, face_bbox)
        
        # Extract eye landmarks (dlib 68-point model)
        # Left eye: points 36-41
        # Right eye: points 42-47
        left_eye_points = np.array([(shape.part(i).x, shape.part(i).y) for i in range(36, 42)])
        right_eye_points = np.array([(shape.part(i).x, shape.part(i).y) for i in range(42, 48)])
        
        left_ear = self.calculate_eye_aspect_ratio(left_eye_points)
        right_ear = self.calculate_eye_aspect_ratio(right_eye_points)
        
        avg_ear = (left_ear + right_ear) / 2.0
        
        return {
            'left_ear': left_ear,
            'right_ear': right_ear,
            'avg_ear': avg_ear,
            'eyes_open': avg_ear > self.EAR_THRESHOLD,
            'left_eye_points': left_eye_points,
            'right_eye_points': right_eye_points
        }
    
    def detect_head_position(self, frame: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Dict:
        """
        Detect head position (tilt, nod)
        
        Args:
            frame: Input frame
            face_bbox: Face bounding box
            
        Returns:
            Dictionary with head position information
        """
        x, y, w, h = face_bbox
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        
        frame_center_x = frame.shape[1] // 2
        frame_center_y = frame.shape[0] // 2
        
        # Calculate head position relative to frame center
        offset_x = face_center_x - frame_center_x
        offset_y = face_center_y - frame_center_y
        
        # Normalize
        normalized_x = offset_x / frame_center_x
        normalized_y = offset_y / frame_center_y
        
        # Determine head position
        head_tilt = "center"
        if abs(normalized_x) > 0.3:
            head_tilt = "left" if normalized_x < 0 else "right"
        
        head_nod = "center"
        if abs(normalized_y) > 0.3:
            head_nod = "up" if normalized_y < 0 else "down"
        
        return {
            'tilt': head_tilt,
            'nod': head_nod,
            'offset': (normalized_x, normalized_y)
        }
    
    def check_drowsiness(self, face_id: str, eyes_open: bool, ear: float = None) -> Dict:
        """
        Check drowsiness based on eye closure patterns
        
        Args:
            face_id: Unique identifier for the face
            eyes_open: Whether eyes are currently open
            ear: Eye aspect ratio (optional)
            
        Returns:
            Dictionary with drowsiness status
        """
        if face_id not in self.eye_closure_counter:
            self.eye_closure_counter[face_id] = 0
            self.eye_closure_history[face_id] = []
        
        if not eyes_open:
            self.eye_closure_counter[face_id] += 1
        else:
            self.eye_closure_counter[face_id] = 0
        
        # Update history
        self.eye_closure_history[face_id].append(1 if not eyes_open else 0)
        if len(self.eye_closure_history[face_id]) > 30:  # Keep last 30 frames
            self.eye_closure_history[face_id].pop(0)
        
        # Calculate drowsiness metrics
        closure_ratio = sum(self.eye_closure_history[face_id]) / len(self.eye_closure_history[face_id])
        
        is_drowsy = self.eye_closure_counter[face_id] >= self.EAR_CONSECUTIVE_FRAMES
        is_sleepy = closure_ratio > 0.5  # Eyes closed more than 50% of the time
        
        drowsiness_level = "awake"
        if is_sleepy:
            drowsiness_level = "sleepy"
        elif is_drowsy:
            drowsiness_level = "drowsy"
        
        return {
            'is_drowsy': is_drowsy,
            'is_sleepy': is_sleepy,
            'drowsiness_level': drowsiness_level,
            'closure_frames': self.eye_closure_counter[face_id],
            'closure_ratio': closure_ratio,
            'ear': ear
        }
    
    def process_frame(self, frame: np.ndarray) -> List[Dict]:
        """
        Process frame to detect sleep/drowsiness
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of dictionaries with sleep detection information
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        results = []
        
        for idx, (x, y, w, h) in enumerate(faces):
            face_id = f"face_{idx}"
            
            # Detect eyes
            if self.predictor:
                # Use dlib for more accurate detection
                dlib_rect = dlib.rectangle(x, y, x+w, y+h)
                eye_data = self.detect_eyes_dlib(frame, dlib_rect)
                ear = eye_data.get('avg_ear', 0.0)
            else:
                # Use OpenCV
                eye_data = self.detect_eyes_opencv(frame, (x, y, w, h))
                ear = None
            
            # Detect head position
            head_position = self.detect_head_position(frame, (x, y, w, h))
            
            # Check drowsiness
            drowsiness = self.check_drowsiness(
                face_id,
                eye_data.get('eyes_open', False),
                ear
            )
            
            results.append({
                'bbox': (x, y, w, h),
                'face_id': face_id,
                'eyes_open': eye_data.get('eyes_open', False),
                'head_position': head_position,
                'drowsiness': drowsiness,
                'eye_data': eye_data
            })
        
        return results






