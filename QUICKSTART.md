# Quick Start Guide

## Step 1: Install Python Dependencies

Open PowerShell or Command Prompt in the project directory and run:

```bash
pip install -r requirements.txt
```

**Note for Windows users:** If `dlib` installation fails, try:
```bash
pip install dlib-binary
```

Or install CMake first:
```bash
pip install cmake
pip install dlib
```

## Step 2: Run the Application

### Option A: Run the Integrated System (All Features)
```bash
python main.py
```

This will run face recognition, mood detection, and sleep detection together.

### Option B: Run Individual Modules

**Face Recognition Only:**
```bash
python example_usage.py face
```

**Mood Detection Only:**
```bash
python example_usage.py mood
```

**Sleep Detection Only:**
```bash
python example_usage.py sleep
```

## Step 3: Controls

- Press **'q'** to quit the application
- Press **'s'** to save a screenshot

## Troubleshooting

### Camera Not Working?
- Make sure your webcam is connected and not being used by another application
- Try different camera indices: `python main.py --camera 1` or `--camera 2`

### Import Errors?
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version (3.8+): `python --version`

### Low Performance?
- The system works best with a good webcam and sufficient lighting
- Close other applications to free up resources

## Adding Known Faces (Optional)

1. Create a folder named `known_faces` in the project directory (it will be created automatically)
2. Add photos of people you want to recognize
3. Name files with the person's name (e.g., `john.jpg`, `jane.png`)
4. The system will automatically recognize these faces when running

## Advanced Options

```bash
# Use specific camera
python main.py --camera 1

# Save output to video file
python main.py --output recording.mp4

# Use dlib predictor for better sleep detection (download shape_predictor_68_face_landmarks.dat first)
python main.py --dlib-predictor shape_predictor_68_face_landmarks.dat
```






