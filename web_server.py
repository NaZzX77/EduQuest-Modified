"""
Flask Web Server for EduQuest
Handles mood detection and attention monitoring for web interface
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import cv2
import numpy as np
import base64
import io
from PIL import Image
import threading
import time
from mood_detection import MoodDetection
from sleep_detection import SleepDetection
from face_detection import FaceRecognition

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize detection modules
mood_detector = MoodDetection()
sleep_detector = SleepDetection()
face_detector = FaceRecognition()

# Global state
active_sessions = {}
mood_data = {}
attention_warnings = {}


def process_image_from_base64(image_data):
    """Convert base64 image to OpenCV format"""
    try:
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to OpenCV format
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        return frame
    except Exception as e:
        print(f"Error processing image: {e}")
        return None


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'EduQuest detection server is running'})


@app.route('/api/mood/start', methods=['POST'])
def start_mood_detection():
    """Start mood detection for a session"""
    data = request.json
    session_id = data.get('session_id', 'default')
    
    active_sessions[session_id] = {
        'type': 'mood',
        'started_at': time.time(),
        'mood_history': []
    }
    
    return jsonify({
        'status': 'success',
        'message': 'Mood detection started',
        'session_id': session_id
    })


@app.route('/api/mood/process', methods=['POST'])
def process_mood():
    """Process frame for mood detection"""
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Process image
        frame = process_image_from_base64(image_data)
        if frame is None:
            return jsonify({'error': 'Failed to process image'}), 400
        
        # Detect mood
        results = mood_detector.process_frame(frame)
        
        if results:
            result = results[0]  # Get first face result
            mood_info = {
                'emotion': result['emotion'],
                'mood': result['mood'],
                'confidence': result['confidence'],
                'scores': result['scores']
            }
            
            # Store in session
            if session_id not in mood_data:
                mood_data[session_id] = []
            mood_data[session_id].append(mood_info)
            
            return jsonify({
                'status': 'success',
                'mood': mood_info
            })
        else:
            return jsonify({
                'status': 'no_face',
                'message': 'No face detected'
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mood/stop', methods=['POST'])
def stop_mood_detection():
    """Stop mood detection and return summary"""
    data = request.json
    session_id = data.get('session_id', 'default')
    
    summary = {
        'total_detections': len(mood_data.get(session_id, [])),
        'mood_history': mood_data.get(session_id, []),
        'dominant_emotion': None,
        'mood_distribution': {}
    }
    
    if mood_data.get(session_id):
        # Calculate dominant emotion
        emotions = [m['emotion'] for m in mood_data[session_id]]
        if emotions:
            from collections import Counter
            emotion_counts = Counter(emotions)
            summary['dominant_emotion'] = emotion_counts.most_common(1)[0][0]
            summary['mood_distribution'] = dict(emotion_counts)
    
    # Clean up
    if session_id in active_sessions:
        del active_sessions[session_id]
    if session_id in mood_data:
        del mood_data[session_id]
    
    return jsonify({
        'status': 'success',
        'summary': summary
    })


@app.route('/api/attention/start', methods=['POST'])
def start_attention_monitoring():
    """Start attention monitoring for demo class"""
    data = request.json
    session_id = data.get('session_id', 'default')
    
    active_sessions[session_id] = {
        'type': 'attention',
        'started_at': time.time(),
        'warnings': [],
        'face_detected_count': 0,
        'no_face_count': 0,
        'look_away_count': 0
    }
    
    return jsonify({
        'status': 'success',
        'message': 'Attention monitoring started',
        'session_id': session_id
    })


@app.route('/api/attention/process', methods=['POST'])
def process_attention():
    """Process frame for attention monitoring"""
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400
        
        # Process image
        frame = process_image_from_base64(image_data)
        if frame is None:
            return jsonify({'error': 'Failed to process image'}), 400
        
        # Detect faces
        face_results = face_detector.process_frame(frame)
        sleep_results = sleep_detector.process_frame(frame)
        
        warning = None
        attention_status = {
            'face_detected': len(face_results) > 0,
            'face_count': len(face_results),
            'looking_at_screen': False,
            'attention_level': 0
        }
        
        if not face_results:
            # No face detected - user not in screen
            if session_id in active_sessions:
                active_sessions[session_id]['no_face_count'] += 1
                no_face_count = active_sessions[session_id]['no_face_count']
                
                # Send warning after 2 seconds (assuming ~30fps, that's ~60 frames)
                if no_face_count > 60:
                    warning = {
                        'type': 'no_face',
                        'message': '⚠️ Warning: You are not visible on screen. Please return to your seat.',
                        'severity': 'high',
                        'timestamp': time.time()
                    }
                    if session_id not in attention_warnings:
                        attention_warnings[session_id] = []
                    attention_warnings[session_id].append(warning)
                    active_sessions[session_id]['warnings'].append(warning)
                    active_sessions[session_id]['no_face_count'] = 0  # Reset counter
        else:
            # Face detected - check if looking at screen
            active_sessions[session_id]['no_face_count'] = 0  # Reset
            active_sessions[session_id]['face_detected_count'] += 1
            
            # Check head position and eye direction
            if sleep_results:
                sleep_result = sleep_results[0]
                head_position = sleep_result.get('head_position', {})
                drowsiness = sleep_result.get('drowsiness', {})
                
                # Check if looking away (head tilt or drowsy)
                tilt = head_position.get('tilt', 'center')
                nod = head_position.get('nod', 'center')
                is_drowsy = drowsiness.get('is_drowsy', False)
                
                if tilt != 'center' or nod != 'center' or is_drowsy:
                    if session_id in active_sessions:
                        active_sessions[session_id]['look_away_count'] += 1
                        look_away_count = active_sessions[session_id]['look_away_count']
                        
                        # Send warning after 1.5 seconds (~45 frames)
                        if look_away_count > 45:
                            warning = {
                                'type': 'look_away',
                                'message': '⚠️ Warning: Please focus on the screen and pay attention to the class.',
                                'severity': 'medium',
                                'timestamp': time.time()
                            }
                            if session_id not in attention_warnings:
                                attention_warnings[session_id] = []
                            attention_warnings[session_id].append(warning)
                            active_sessions[session_id]['warnings'].append(warning)
                            active_sessions[session_id]['look_away_count'] = 0  # Reset
                else:
                    # Looking at screen
                    attention_status['looking_at_screen'] = True
                    attention_status['attention_level'] = 100
                    if session_id in active_sessions:
                        active_sessions[session_id]['look_away_count'] = 0
        
        return jsonify({
            'status': 'success',
            'attention': attention_status,
            'warning': warning
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/attention/stop', methods=['POST'])
def stop_attention_monitoring():
    """Stop attention monitoring and return summary"""
    data = request.json
    session_id = data.get('session_id', 'default')
    
    summary = {
        'total_warnings': len(attention_warnings.get(session_id, [])),
        'warnings': attention_warnings.get(session_id, []),
        'session_duration': 0
    }
    
    if session_id in active_sessions:
        summary['session_duration'] = time.time() - active_sessions[session_id]['started_at']
        summary['face_detected_count'] = active_sessions[session_id].get('face_detected_count', 0)
        summary['no_face_count'] = active_sessions[session_id].get('no_face_count', 0)
        summary['look_away_count'] = active_sessions[session_id].get('look_away_count', 0)
    
    # Clean up
    if session_id in active_sessions:
        del active_sessions[session_id]
    if session_id in attention_warnings:
        del attention_warnings[session_id]
    
    return jsonify({
        'status': 'success',
        'summary': summary
    })


if __name__ == '__main__':
    print("Starting EduQuest Detection Server...")
    print("Server will run on http://localhost:5000")
    print("Make sure to allow CORS in your browser if testing locally")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)






