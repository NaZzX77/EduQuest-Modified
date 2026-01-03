"""
Main Application
Integrates face recognition, mood detection, and sleep detection
"""

import cv2
import numpy as np
import argparse
from typing import Dict, List
import time

from face_detection import FaceRecognition
from mood_detection import MoodDetection
from sleep_detection import SleepDetection


class IntegratedDetectionSystem:
    """Integrated system for face recognition, mood, and sleep detection"""
    
    def __init__(self, known_faces_dir: str = "known_faces", 
                 emotion_model_path: str = None,
                 dlib_predictor_path: str = None):
        """
        Initialize integrated detection system
        
        Args:
            known_faces_dir: Directory with known face images
            emotion_model_path: Path to emotion detection model
            dlib_predictor_path: Path to dlib shape predictor
        """
        self.face_recognition = FaceRecognition(known_faces_dir)
        self.mood_detection = MoodDetection(emotion_model_path)
        self.sleep_detection = SleepDetection(dlib_predictor_path)
        
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
    
    def draw_results(self, frame: np.ndarray, results: Dict) -> np.ndarray:
        """
        Draw detection results on frame
        
        Args:
            frame: Input frame
            results: Combined detection results
            
        Returns:
            Frame with annotations
        """
        x, y, w, h = results['bbox']
        
        # Draw bounding box
        color = (0, 255, 0)  # Green for normal
        if results.get('drowsiness', {}).get('is_sleepy', False):
            color = (0, 0, 255)  # Red for sleepy
        elif results.get('drowsiness', {}).get('is_drowsy', False):
            color = (0, 165, 255)  # Orange for drowsy
        
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        
        # Prepare text information
        info_lines = []
        
        # Face recognition
        if results.get('name'):
            info_lines.append(f"Name: {results['name']}")
        
        # Mood detection
        if results.get('emotion'):
            emotion = results['emotion']
            mood = results.get('mood', 'neutral')
            confidence = results.get('emotion_confidence', 0)
            info_lines.append(f"Emotion: {emotion} ({mood}) [{confidence:.2f}]")
        
        # Sleep detection
        if results.get('drowsiness'):
            drowsiness = results['drowsiness']
            drowsiness_level = drowsiness.get('drowsiness_level', 'awake')
            info_lines.append(f"Status: {drowsiness_level}")
            
            if drowsiness.get('ear'):
                info_lines.append(f"EAR: {drowsiness['ear']:.3f}")
        
        # Draw text background
        text_y = y - 10
        for i, line in enumerate(info_lines):
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(
                frame,
                (x, text_y - 15 - i * 20),
                (x + text_size[0] + 10, text_y - i * 20),
                (0, 0, 0),
                -1
            )
            cv2.putText(
                frame,
                line,
                (x + 5, text_y - 5 - i * 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
        
        return frame
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a single frame with all detection systems
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Annotated frame
        """
        # Get face locations from face recognition
        face_results = self.face_recognition.process_frame(frame)
        
        # Process each detected face
        for face_result in face_results:
            top, right, bottom, left = face_result['location']
            x, y, w, h = left, top, right - left, bottom - top
            
            # Combine results
            combined_result = {
                'bbox': (x, y, w, h),
                'name': face_result.get('name', 'Unknown')
            }
            
            # Mood detection
            mood_results = self.mood_detection.process_frame(frame)
            for mood_result in mood_results:
                mx, my, mw, mh = mood_result['bbox']
                # Check if this mood result corresponds to the same face
                if abs(mx - x) < w and abs(my - y) < h:
                    combined_result['emotion'] = mood_result['emotion']
                    combined_result['mood'] = mood_result['mood']
                    combined_result['emotion_confidence'] = mood_result['confidence']
                    break
            
            # Sleep detection
            sleep_results = self.sleep_detection.process_frame(frame)
            for sleep_result in sleep_results:
                sx, sy, sw, sh = sleep_result['bbox']
                # Check if this sleep result corresponds to the same face
                if abs(sx - x) < w and abs(sy - y) < h:
                    combined_result['drowsiness'] = sleep_result['drowsiness']
                    combined_result['head_position'] = sleep_result['head_position']
                    break
            
            # Draw results
            frame = self.draw_results(frame, combined_result)
        
        # Calculate and display FPS
        self.fps_counter += 1
        if time.time() - self.fps_start_time >= 1.0:
            self.current_fps = self.fps_counter
            self.fps_counter = 0
            self.fps_start_time = time.time()
        
        cv2.putText(
            frame,
            f"FPS: {self.current_fps}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        
        return frame
    
    def run(self, camera_index: int = 0, output_file: str = None):
        """
        Run the integrated detection system
        
        Args:
            camera_index: Camera device index
            output_file: Optional output video file path
        """
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            print(f"Error: Could not open camera {camera_index}")
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Video writer if output file is specified
        writer = None
        if output_file:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 20.0
            frame_size = (640, 480)
            writer = cv2.VideoWriter(output_file, fourcc, fps, frame_size)
        
        print("Starting detection system...")
        print("Press 'q' to quit, 's' to save screenshot")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame
                annotated_frame = self.process_frame(frame)
                
                # Write to output file if specified
                if writer:
                    writer.write(annotated_frame)
                
                # Display frame
                cv2.imshow('Face Recognition, Mood & Sleep Detection', annotated_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    screenshot_path = f"screenshot_{int(time.time())}.jpg"
                    cv2.imwrite(screenshot_path, annotated_frame)
                    print(f"Screenshot saved: {screenshot_path}")
        
        except KeyboardInterrupt:
            print("\nStopping detection system...")
        
        finally:
            cap.release()
            if writer:
                writer.release()
            cv2.destroyAllWindows()
            print("System stopped.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Integrated Face Recognition, Mood Detection, and Sleep Detection System'
    )
    parser.add_argument(
        '--camera',
        type=int,
        default=0,
        help='Camera device index (default: 0)'
    )
    parser.add_argument(
        '--known-faces',
        type=str,
        default='known_faces',
        help='Directory containing known face images (default: known_faces)'
    )
    parser.add_argument(
        '--emotion-model',
        type=str,
        default=None,
        help='Path to emotion detection model'
    )
    parser.add_argument(
        '--dlib-predictor',
        type=str,
        default=None,
        help='Path to dlib shape predictor (shape_predictor_68_face_landmarks.dat)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output video file path (optional)'
    )
    
    args = parser.parse_args()
    
    # Create and run system
    system = IntegratedDetectionSystem(
        known_faces_dir=args.known_faces,
        emotion_model_path=args.emotion_model,
        dlib_predictor_path=args.dlib_predictor
    )
    
    system.run(camera_index=args.camera, output_file=args.output)


if __name__ == "__main__":
    main()







