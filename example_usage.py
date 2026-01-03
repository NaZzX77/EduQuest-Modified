"""
Example usage of individual modules
Demonstrates how to use each module separately
"""

import cv2
from face_detection import FaceRecognition
from mood_detection import MoodDetection
from sleep_detection import SleepDetection


def example_face_recognition():
    """Example: Using face recognition only"""
    print("=== Face Recognition Example ===")
    
    # Initialize face recognition
    face_rec = FaceRecognition(known_faces_dir="known_faces")
    
    # Add a new face (optional)
    # face_rec.add_face("path/to/image.jpg", "Person Name")
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    print("Press 'q' to quit")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process frame
        results = face_rec.process_frame(frame)
        
        # Draw results
        for result in results:
            top, right, bottom, left = result['location']
            name = result['name']
            
            # Draw rectangle
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            
            # Draw name
            cv2.putText(
                frame,
                name,
                (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2
            )
        
        cv2.imshow('Face Recognition', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def example_mood_detection():
    """Example: Using mood detection only"""
    print("=== Mood Detection Example ===")
    
    # Initialize mood detection
    mood_det = MoodDetection()
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    print("Press 'q' to quit")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process frame
        results = mood_det.process_frame(frame)
        
        # Draw results
        for result in results:
            x, y, w, h = result['bbox']
            emotion = result['emotion']
            mood = result['mood']
            confidence = result['confidence']
            
            # Choose color based on mood
            color = (0, 255, 0) if mood == 'positive' else \
                   (0, 0, 255) if mood == 'negative' else (128, 128, 128)
            
            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # Draw emotion info
            text = f"{emotion} ({mood}) [{confidence:.2f}]"
            cv2.putText(
                frame,
                text,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )
        
        cv2.imshow('Mood Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def example_sleep_detection():
    """Example: Using sleep detection only"""
    print("=== Sleep Detection Example ===")
    
    # Initialize sleep detection
    # Optionally provide dlib predictor path for better accuracy
    sleep_det = SleepDetection()  # or SleepDetection(predictor_path="shape_predictor_68_face_landmarks.dat")
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    print("Press 'q' to quit")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Process frame
        results = sleep_det.process_frame(frame)
        
        # Draw results
        for result in results:
            x, y, w, h = result['bbox']
            drowsiness = result['drowsiness']
            level = drowsiness['drowsiness_level']
            
            # Choose color based on drowsiness level
            if level == 'sleepy':
                color = (0, 0, 255)  # Red
            elif level == 'drowsy':
                color = (0, 165, 255)  # Orange
            else:
                color = (0, 255, 0)  # Green
            
            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # Draw status
            text = f"Status: {level}"
            if drowsiness.get('ear'):
                text += f" (EAR: {drowsiness['ear']:.3f})"
            
            cv2.putText(
                frame,
                text,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )
        
        cv2.imshow('Sleep Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "face":
            example_face_recognition()
        elif mode == "mood":
            example_mood_detection()
        elif mode == "sleep":
            example_sleep_detection()
        else:
            print("Usage: python example_usage.py [face|mood|sleep]")
    else:
        print("Usage: python example_usage.py [face|mood|sleep]")
        print("\nExamples:")
        print("  python example_usage.py face   - Run face recognition only")
        print("  python example_usage.py mood   - Run mood detection only")
        print("  python example_usage.py sleep  - Run sleep detection only")







