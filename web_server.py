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
# Track eye closure duration for sleepiness detection (using actual time)
EYE_CLOSURE_THRESHOLD_MIN = 3.0  # 3 seconds
EYE_CLOSURE_THRESHOLD_MAX = 5.0  # 5 seconds


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
    """Process frame for mood detection with focus and sleepiness detection"""
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
        mood_results = mood_detector.process_frame(frame)
        
        # Detect sleepiness and focus
        sleep_results = sleep_detector.process_frame(frame)
        face_results = face_detector.process_frame(frame)
        
        # Initialize session tracking if needed
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                'type': 'mood',
                'eye_closure_start_time': None,
                'focus_time': 0,
                'distractions': 0,
                'attention_level': 0,
                'last_warning_time': 0
            }
        
        session = active_sessions[session_id]
        current_time = time.time()
        warning = None
        sleepiness_status = {
            'eyes_open': True,
            'closure_duration': 0,
            'is_sleepy': False
        }
        focus_status = {
            'face_detected': len(face_results) > 0,
            'looking_at_screen': False,
            'attention_level': 0
        }
        
        if sleep_results:
            sleep_result = sleep_results[0]
            drowsiness = sleep_result.get('drowsiness', {})
            eye_data = sleep_result.get('eye_data', {})
            
            # Get eyes_open from sleep result
            eyes_open = sleep_result.get('eyes_open', True)
            
            # Additional check: if no eyes detected but face is detected, eyes are likely closed
            if face_results and len(face_results) > 0:
                eyes_detected = eye_data.get('eyes_detected', 0)
                # If face is detected but no eyes detected, eyes are definitely closed
                if eyes_detected == 0:
                    eyes_open = False
                elif eyes_detected == 1:
                    # Only one eye detected - assume closed (need both eyes)
                    eyes_open = False
                elif eyes_detected > 1:
                    # Eyes detected - check area ratio for better accuracy
                    eye_area_ratio = eye_data.get('eye_area_ratio', 0)
                    # More aggressive - need at least 2.5% to be considered open
                    if eye_area_ratio < 0.025:  # Very small eye area - likely closed
                        eyes_open = False
            
            sleepiness_status['eyes_open'] = eyes_open
            
            if not eyes_open:
                # Eyes closed - start tracking time
                if session['eye_closure_start_time'] is None:
                    session['eye_closure_start_time'] = current_time
                
                closure_duration = current_time - session['eye_closure_start_time']
                sleepiness_status['closure_duration'] = closure_duration
                
                # Check if eyes closed for 3-5 seconds
                if closure_duration >= EYE_CLOSURE_THRESHOLD_MIN:
                    sleepiness_status['is_sleepy'] = True
                    
                    # Only send warning if we haven't sent one in the last 5 seconds
                    if current_time - session.get('last_warning_time', 0) >= 5.0:
                        warning = {
                            'type': 'sleepiness',
                            'message': '😴 Warning: You appear to be sleepy! Please open your eyes and stay alert.',
                            'severity': 'high',
                            'play_sound': True,
                            'timestamp': current_time,
                            'closure_duration': closure_duration
                        }
                        session['last_warning_time'] = current_time
            else:
                # Eyes open - reset tracking immediately
                session['eye_closure_start_time'] = None
                sleepiness_status['closure_duration'] = 0
                sleepiness_status['is_sleepy'] = False  # Reset sleepy status when eyes open
        
        # Focus detection using computer vision
        if face_results:
            focus_status['face_detected'] = True
            
            if sleep_results:
                sleep_result = sleep_results[0]
                head_position = sleep_result.get('head_position', {})
                tilt = head_position.get('tilt', 'center')
                nod = head_position.get('nod', 'center')
                eyes_open = sleepiness_status['eyes_open']
                eye_data = sleep_result.get('eye_data', {})
                
                # Calculate attention level based on multiple factors
                attention_score = 0
                
                # Face detected: +30 points
                attention_score += 30
                
                # Eyes open: +40 points
                if eyes_open:
                    attention_score += 40
                else:
                    attention_score -= 20  # Penalty for closed eyes
                
                # Head position (looking at screen): +30 points
                if tilt == 'center' and nod == 'center':
                    attention_score += 30
                elif abs(head_position.get('offset', [0, 0])[0]) < 0.2 and abs(head_position.get('offset', [0, 0])[1]) < 0.2:
                    attention_score += 20  # Slight deviation
                else:
                    attention_score -= 15  # Looking away
                
                # Use EAR (Eye Aspect Ratio) if available for more accurate detection
                if eye_data.get('avg_ear'):
                    ear = eye_data.get('avg_ear', 0)
                    if ear > 0.3:  # Eyes clearly open
                        attention_score += 10
                    elif ear < 0.2:  # Eyes clearly closed
                        attention_score -= 10
                
                # Clamp attention level between 0 and 100
                attention_score = max(0, min(100, attention_score))
                focus_status['attention_level'] = attention_score
                
                # Determine if looking at screen
                if tilt == 'center' and nod == 'center' and eyes_open and attention_score >= 70:
                    focus_status['looking_at_screen'] = True
                    session['focus_time'] = session.get('focus_time', 0) + 1
                else:
                    focus_status['looking_at_screen'] = False
            else:
                # Face detected but no sleep results - assume moderate attention
                focus_status['attention_level'] = 50
                focus_status['looking_at_screen'] = False
        else:
            # No face detected
            focus_status['face_detected'] = False
            focus_status['attention_level'] = 0
            focus_status['looking_at_screen'] = False
        
        session['attention_level'] = focus_status['attention_level']
        
        if mood_results:
            result = mood_results[0]  # Get first face result
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
                'mood': mood_info,
                'sleepiness': sleepiness_status,
                'focus': focus_status,
                'warning': warning
            })
        else:
            return jsonify({
                'status': 'no_face',
                'message': 'No face detected',
                'sleepiness': sleepiness_status,
                'focus': focus_status,
                'warning': warning
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
            
            # Check head position, eye direction, and sleepiness
            if sleep_results:
                sleep_result = sleep_results[0]
                head_position = sleep_result.get('head_position', {})
                drowsiness = sleep_result.get('drowsiness', {})
                eye_data = sleep_result.get('eye_data', {})
                eyes_open = sleep_result.get('eyes_open', True)
                
                # Use computer vision EAR for more accurate eye detection
                if eye_data.get('avg_ear') is not None:
                    ear = eye_data.get('avg_ear', 0)
                    eyes_open = ear > 0.25  # EAR threshold for open eyes
                
                # Additional check: if no eyes detected but face is detected, eyes are likely closed
                eyes_detected = eye_data.get('eyes_detected', 0)
                if eyes_detected == 0 and len(face_results) > 0:
                    # Face detected but no eyes - definitely closed
                    eyes_open = False
                elif eyes_detected == 1:
                    # Only one eye detected - assume closed (need both eyes)
                    eyes_open = False
                elif eyes_detected > 1:
                    # Eyes detected - check area ratio for better accuracy
                    eye_area_ratio = eye_data.get('eye_area_ratio', 0)
                    # More aggressive - need at least 2.5% to be considered open
                    if eye_area_ratio < 0.025:  # Very small eye area - likely closed
                        eyes_open = False
                
                # Initialize eye closure tracking if needed
                if 'eye_closure_start_time' not in active_sessions[session_id]:
                    active_sessions[session_id]['eye_closure_start_time'] = None
                    active_sessions[session_id]['last_warning_time'] = 0
                
                current_time = time.time()
                session = active_sessions[session_id]
                
                # Check sleepiness (eyes closed for 3-5 seconds) using computer vision
                if not eyes_open:
                    # Eyes closed - start tracking time
                    if session['eye_closure_start_time'] is None:
                        session['eye_closure_start_time'] = current_time
                    
                    closure_duration = current_time - session['eye_closure_start_time']
                    
                    # Check if eyes closed for 3-5 seconds
                    if closure_duration >= EYE_CLOSURE_THRESHOLD_MIN:
                        # Only send warning if we haven't sent one in the last 5 seconds
                        if current_time - session.get('last_warning_time', 0) >= 5.0:
                            warning = {
                                'type': 'sleepiness',
                                'message': '😴 Warning: You appear to be sleepy! Please open your eyes and stay alert.',
                                'severity': 'high',
                                'play_sound': True,
                                'timestamp': current_time,
                                'closure_duration': closure_duration
                            }
                            if session_id not in attention_warnings:
                                attention_warnings[session_id] = []
                            attention_warnings[session_id].append(warning)
                            session['warnings'].append(warning)
                            session['last_warning_time'] = current_time
                else:
                    # Eyes open - reset tracking immediately
                    session['eye_closure_start_time'] = None
                    # Reset closure duration in response
                    if 'sleepiness_status' in locals():
                        sleepiness_status['closure_duration'] = 0
                        sleepiness_status['is_sleepy'] = False
                
                # Get eye data for better detection
                eye_data = sleep_result.get('eye_data', {})
                
                # Check if looking away (head tilt or nod)
                tilt = head_position.get('tilt', 'center')
                nod = head_position.get('nod', 'center')
                is_drowsy = drowsiness.get('is_drowsy', False)
                
                # Calculate attention level using computer vision data
                attention_score = 0
                
                # Face detected: +30 points
                attention_score += 30
                
                # Eyes open: +40 points
                if eyes_open:
                    attention_score += 40
                else:
                    attention_score -= 20
                
                # Head position: +30 points if centered
                if tilt == 'center' and nod == 'center':
                    attention_score += 30
                else:
                    attention_score -= 15
                
                # Use EAR if available for more accurate detection
                if eye_data.get('avg_ear') is not None:
                    ear = eye_data.get('avg_ear', 0)
                    if ear > 0.3:  # Eyes clearly open
                        attention_score += 10
                    elif ear < 0.2:  # Eyes clearly closed
                        attention_score -= 10
                
                attention_score = max(0, min(100, attention_score))
                attention_status['attention_level'] = attention_score
                
                if tilt != 'center' or nod != 'center' or is_drowsy or not eyes_open:
                    if session_id in active_sessions:
                        active_sessions[session_id]['look_away_count'] += 1
                        look_away_count = active_sessions[session_id]['look_away_count']
                        
                        # Send warning after 1.5 seconds (~45 frames)
                        if look_away_count > 45:
                            if not warning:  # Don't override sleepiness warning
                                warning = {
                                    'type': 'look_away',
                                    'message': '⚠️ Warning: Please focus on the screen and pay attention to the class.',
                                    'severity': 'medium',
                                    'play_sound': False,
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
                    if session_id in active_sessions:
                        active_sessions[session_id]['look_away_count'] = 0
                        active_sessions[session_id]['focus_time'] = active_sessions[session_id].get('focus_time', 0) + 1
        
        # Add sleepiness status to response
        sleepiness_status = {
            'eyes_open': True,
            'closure_duration': 0,
            'is_sleepy': False
        }
        
        if sleep_results:
            sleep_result = sleep_results[0]
            eye_data = sleep_result.get('eye_data', {})
            eyes_open = sleep_result.get('eyes_open', True)
            
            # Additional check: if no eyes detected but face is detected, eyes are likely closed
            eyes_detected = eye_data.get('eyes_detected', 0)
            if eyes_detected == 0 and len(face_results) > 0:
                # Face detected but no eyes - definitely closed
                eyes_open = False
            elif eyes_detected == 1:
                # Only one eye detected - assume closed (need both eyes)
                eyes_open = False
            elif eyes_detected > 1:
                # Eyes detected - check area ratio for better accuracy
                eye_area_ratio = eye_data.get('eye_area_ratio', 0)
                # More aggressive - need at least 2.5% to be considered open
                if eye_area_ratio < 0.025:  # Very small eye area - likely closed
                    eyes_open = False
            
            sleepiness_status['eyes_open'] = eyes_open
            
            if session_id in active_sessions:
                session = active_sessions[session_id]
                if eyes_open:
                    # Eyes are open - reset everything immediately
                    session['eye_closure_start_time'] = None
                    sleepiness_status['closure_duration'] = 0
                    sleepiness_status['is_sleepy'] = False
                elif session.get('eye_closure_start_time') is not None:
                    # Eyes closed - track duration
                    closure_duration = time.time() - session['eye_closure_start_time']
                    sleepiness_status['closure_duration'] = closure_duration
                    sleepiness_status['is_sleepy'] = closure_duration >= EYE_CLOSURE_THRESHOLD_MIN
                else:
                    # Just started closing
                    sleepiness_status['closure_duration'] = 0
                    sleepiness_status['is_sleepy'] = False
        
        return jsonify({
            'status': 'success',
            'attention': attention_status,
            'sleepiness': sleepiness_status,
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







