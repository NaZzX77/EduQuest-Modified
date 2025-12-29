# Face Recognition, Mood Detection & Sleep Detection System

A comprehensive Python-based system that integrates face recognition, emotion/mood detection, and sleep/drowsiness detection using computer vision and machine learning.

## Features

- **Face Recognition**: Detect and recognize known faces from a database
- **Mood Detection**: Analyze facial expressions to detect emotions (happy, sad, angry, neutral, etc.)
- **Sleep Detection**: Monitor eye closure patterns and head position to detect drowsiness and sleepiness

## Project Structure

```
eduquest/
├── face_detection/
│   ├── __init__.py
│   └── face_recognition_module.py
├── mood_detection/
│   ├── __init__.py
│   └── mood_detection_module.py
├── sleep_detection/
│   ├── __init__.py
│   └── sleep_detection_module.py
├── main.py
├── requirements.txt
├── README.md
└── known_faces/          # Directory for known face images (created automatically)
```

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install dlib (if needed):**
   
   For Windows:
   ```bash
   pip install dlib
   ```
   
   For Linux/Mac, you may need to install system dependencies first:
   ```bash
   sudo apt-get install cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev
   pip install dlib
   ```

3. **Download dlib shape predictor (optional, for better sleep detection):**
   
   Download `shape_predictor_68_face_landmarks.dat` from:
   http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
   
   Extract it and place it in the project directory.

## Usage

### Basic Usage

Run the system with default settings:
```bash
python main.py
```

### Advanced Usage

```bash
# Use a specific camera
python main.py --camera 1

# Specify known faces directory
python main.py --known-faces ./my_faces

# Use dlib predictor for better sleep detection
python main.py --dlib-predictor shape_predictor_68_face_landmarks.dat

# Save output to video file
python main.py --output output.mp4

# Combine options
python main.py --camera 0 --dlib-predictor shape_predictor_68_face_landmarks.dat --output recording.mp4
```

### Adding Known Faces

1. Create a `known_faces` directory (or use your custom directory)
2. Add images of people you want to recognize
3. Name the files with the person's name (e.g., `john.jpg`, `jane.png`)
4. The system will automatically encode and recognize these faces

Example:
```
known_faces/
├── john.jpg
├── jane.png
└── mike.jpeg
```

## Controls

- **'q'**: Quit the application
- **'s'**: Save a screenshot

## Module Details

### Face Recognition Module
- Uses `face_recognition` library for face detection and encoding
- Supports adding new faces dynamically
- Stores encodings in pickle format for faster loading

### Mood Detection Module
- Detects 7 emotions: angry, disgust, fear, happy, neutral, sad, surprise
- Categorizes emotions into mood categories: positive, negative, neutral
- Can be extended with custom ML models for better accuracy

### Sleep Detection Module
- Monitors eye closure using Eye Aspect Ratio (EAR)
- Tracks head position and tilt
- Detects drowsiness and sleepiness based on eye closure patterns
- Supports both OpenCV and dlib-based detection (dlib is more accurate)

## Customization

### Adding Custom Emotion Models

Edit `mood_detection/mood_detection_module.py` and implement the `predict_emotion_with_model()` method with your trained model.

### Adjusting Sleep Detection Sensitivity

Edit `sleep_detection/sleep_detection_module.py`:
- `EAR_THRESHOLD`: Lower values = more sensitive to eye closure
- `EAR_CONSECUTIVE_FRAMES`: Number of frames with closed eyes before alerting

## Requirements

- Python 3.8+
- Webcam or camera device
- OpenCV
- face_recognition
- dlib (optional but recommended)
- numpy

## Notes

- The mood detection uses a simple rule-based approach by default. For production use, integrate a trained emotion detection model.
- Sleep detection works best with dlib shape predictor for accurate eye landmark detection.
- Performance may vary depending on hardware and camera quality.

## Troubleshooting

**Camera not working:**
- Check camera permissions
- Try different camera indices (--camera 0, 1, 2, etc.)

**dlib installation issues:**
- On Windows, use pre-built wheels: `pip install dlib-binary`
- On Linux, ensure CMake and required libraries are installed

**Low FPS:**
- Reduce camera resolution in `main.py`
- Use GPU acceleration if available
- Disable dlib predictor if not needed

## License

This project is provided as-is for educational purposes.






