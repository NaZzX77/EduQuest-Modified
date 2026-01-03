"""
Attention Monitoring Module
Monitors user attention and sends warnings when user looks away or is not in screen
"""

import cv2
import numpy as np
from typing import Dict, List, Optional
from face_detection import FaceRecognition
from sleep_detection import SleepDetection


class AttentionMonitor:
    """Monitor user attention and detect when they look away"""
    
    def __init__(self, warning_threshold_no_face: int = 60, 
                 warning_threshold_look_away: int = 45):
        """
        Initialize attention monitor
        
        Args:
            warning_threshold_no_face: Frames without face before warning (default: 60 = ~2 seconds at 30fps)
            warning_threshold_look_away: Frames looking away before warning (default: 45 = ~1.5 seconds at 30fps)
        """
        self.face_detector = FaceRecognition()
        self.sleep_detector = SleepDetection()
        
        self.warning_threshold_no_face = warning_threshold_no_face
        self.warning_threshold_look_away = warning_threshold_look_away
        
        self.no_face_counter = 0
        self.look_away_counter = 0
        self.warnings = []
    
    def check_attention(self, frame: np.ndarray) -> Dict:
        """
        Check user attention in frame
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Dictionary with attention status and warnings
        """
        face_results = self.face_detector.process_frame(frame)
        sleep_results = self.sleep_detector.process_frame(frame)
        
        result = {
            'face_detected': len(face_results) > 0,
            'looking_at_screen': False,
            'attention_level': 0,
            'warning': None
        }
        
        if not face_results:
            # No face detected
            self.no_face_counter += 1
            self.look_away_counter = 0
            
            if self.no_face_counter >= self.warning_threshold_no_face:
                result['warning'] = {
                    'type': 'no_face',
                    'message': '⚠️ Warning: You are not visible on screen. Please return to your seat.',
                    'severity': 'high'
                }
                self.warnings.append(result['warning'])
                self.no_face_counter = 0  # Reset after warning
        else:
            # Face detected
            self.no_face_counter = 0
            
            if sleep_results:
                sleep_result = sleep_results[0]
                head_position = sleep_result.get('head_position', {})
                drowsiness = sleep_result.get('drowsiness', {})
                
                tilt = head_position.get('tilt', 'center')
                nod = head_position.get('nod', 'center')
                is_drowsy = drowsiness.get('is_drowsy', False)
                
                # Check if looking away
                if tilt != 'center' or nod != 'center' or is_drowsy:
                    self.look_away_counter += 1
                    
                    if self.look_away_counter >= self.warning_threshold_look_away:
                        result['warning'] = {
                            'type': 'look_away',
                            'message': '⚠️ Warning: Please focus on the screen and pay attention to the class.',
                            'severity': 'medium'
                        }
                        self.warnings.append(result['warning'])
                        self.look_away_counter = 0  # Reset after warning
                else:
                    # Looking at screen
                    result['looking_at_screen'] = True
                    result['attention_level'] = 100
                    self.look_away_counter = 0
        
        return result
    
    def get_warnings(self) -> List[Dict]:
        """Get all warnings generated"""
        return self.warnings
    
    def reset(self):
        """Reset counters and warnings"""
        self.no_face_counter = 0
        self.look_away_counter = 0
        self.warnings = []







