# Setup Instructions for EduQuest Detection System

## Step 1: Install Python Dependencies

Open a terminal/command prompt in the project directory and run:

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

## Step 2: Start the Flask Server

### Windows:
Double-click `START_SERVER.bat` or run:
```bash
python web_server.py
```

### Linux/Mac:
```bash
chmod +x START_SERVER.sh
./START_SERVER.sh
```

Or directly:
```bash
python3 web_server.py
```

The server will start on `http://localhost:5000`

## Step 3: Open the HTML File

1. Open `eduquest.html` in your web browser
2. Make sure the Flask server is running (Step 2)
3. The browser will connect to the server automatically

## Step 4: Test the Features

### Test Mood Detection:
1. Click "Student Login" (or sign up)
2. Click "Take Test"
3. Mood detection will start automatically
4. You'll see mood indicators in the top-right corner

### Test Attention Monitoring (Demo Class):
1. Click "Take Demo"
2. Click "Start Demo"
3. Allow camera access when prompted
4. Try looking away from the screen or leaving the frame
5. You should see warning messages appear

## Troubleshooting

### Server Connection Error
- Make sure the Flask server is running on port 5000
- Check if another application is using port 5000
- Try changing the port in `web_server.py` and `eduquest.html`

### Camera Not Working
- Make sure you've granted camera permissions in your browser
- Check if another application is using the camera
- Try refreshing the page

### CORS Errors
- The Flask server has CORS enabled, but if you still see errors:
  - Make sure you're accessing the HTML file via `file://` protocol
  - Or use a local web server like `python -m http.server 8000`

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version (3.8+): `python --version`

## API Endpoints

The server provides these endpoints:

- `GET /api/health` - Health check
- `POST /api/mood/start` - Start mood detection session
- `POST /api/mood/process` - Process frame for mood detection
- `POST /api/mood/stop` - Stop mood detection and get summary
- `POST /api/attention/start` - Start attention monitoring
- `POST /api/attention/process` - Process frame for attention monitoring
- `POST /api/attention/stop` - Stop attention monitoring and get summary

## Features

✅ **Mood Detection**: Automatically starts when test begins
✅ **Attention Monitoring**: Warns when user looks away or is not in screen
✅ **Real-time Processing**: Processes video frames in real-time
✅ **Warning System**: Visual warnings for inattention







