"""
Face Recognition Module
Detects and recognizes faces using OpenCV and face_recognition library
"""

import cv2
import face_recognition
import numpy as np
import os
import pickle
from typing import List, Tuple, Optional


class FaceRecognition:
    """Face recognition and detection class"""
    
    def __init__(self, known_faces_dir: str = "known_faces"):
        """
        Initialize face recognition system
        
        Args:
            known_faces_dir: Directory containing known face images
        """
        self.known_faces_dir = known_faces_dir
        self.known_face_encodings = []
        self.known_face_names = []
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known faces from directory or pickle file"""
        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir)
            return
        
        # Try to load from pickle file first
        pickle_file = os.path.join(self.known_faces_dir, "encodings.pkl")
        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as f:
                data = pickle.load(f)
                self.known_face_encodings = data['encodings']
                self.known_face_names = data['names']
            return
        
        # Load from images
        for filename in os.listdir(self.known_faces_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(self.known_faces_dir, filename)
                image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(image)
                
                if encodings:
                    self.known_face_encodings.append(encodings[0])
                    self.known_face_names.append(os.path.splitext(filename)[0])
        
        # Save to pickle for faster loading next time
        if self.known_face_encodings:
            self.save_encodings()
    
    def save_encodings(self):
        """Save face encodings to pickle file"""
        pickle_file = os.path.join(self.known_faces_dir, "encodings.pkl")
        with open(pickle_file, 'wb') as f:
            pickle.dump({
                'encodings': self.known_face_encodings,
                'names': self.known_face_names
            }, f)
    
    def add_face(self, image_path: str, name: str):
        """
        Add a new face to the known faces database
        
        Args:
            image_path: Path to the image file
            name: Name of the person
        """
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        
        if encodings:
            self.known_face_encodings.append(encodings[0])
            self.known_face_names.append(name)
            self.save_encodings()
            return True
        return False
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in a frame
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of face locations (top, right, bottom, left)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        return face_locations
    
    def recognize_face(self, frame: np.ndarray, face_location: Tuple[int, int, int, int]) -> Optional[str]:
        """
        Recognize a face in the frame
        
        Args:
            frame: Input frame (BGR format)
            face_location: Face location tuple (top, right, bottom, left)
            
        Returns:
            Name of the recognized person or None
        """
        if not self.known_face_encodings:
            return None
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_encoding = face_recognition.face_encodings(rgb_frame, [face_location])
        
        if not face_encoding:
            return None
        
        matches = face_recognition.compare_faces(
            self.known_face_encodings, 
            face_encoding[0],
            tolerance=0.6
        )
        face_distances = face_recognition.face_distance(
            self.known_face_encodings, 
            face_encoding[0]
        )
        
        best_match_index = np.argmin(face_distances)
        
        if matches[best_match_index] and face_distances[best_match_index] < 0.6:
            return self.known_face_names[best_match_index]
        
        return None
    
    def process_frame(self, frame: np.ndarray) -> List[dict]:
        """
        Process a frame to detect and recognize faces
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of dictionaries with face information
        """
        face_locations = self.detect_faces(frame)
        results = []
        
        for face_location in face_locations:
            top, right, bottom, left = face_location
            name = self.recognize_face(frame, face_location)
            
            results.append({
                'location': face_location,
                'name': name if name else 'Unknown',
                'bbox': (left, top, right - left, bottom - top)
            })
        
        return results






