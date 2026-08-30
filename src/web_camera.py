import os
import sys
import time
import datetime
import threading
import subprocess
import cv2
from flask import Flask, Response, render_template_string, jsonify, request

app = Flask(__name__)

PHOTO_DIR = os.path.expanduser(r"~\Pictures\Camera Roll")
VIDEO_DIR = os.path.expanduser(r"~\Videos")
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

class CameraStream:
    def __init__(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.mirror = True
        self.last_frame = None
        self.lock = threading.Lock()
        
        # Video Recording State
        self.is_recording = False
        self.video_writer = None
        self.record_start_time = 0
        self.record_filename = ""
        self.record_path = ""

    def get_frame_bytes(self):
        with self.lock:
            if not self.cap or not self.cap.isOpened():
                return None
            ret, frame = self.cap.read()
            if not ret:
                return None
            
            if self.mirror:
                frame = cv2.flip(frame, 1)
            
            self.last_frame = frame.copy()
            
            # Write to video recording if active
            if self.is_recording and self.video_writer is not None:
                self.video_writer.write(frame)
            
            # Encode to JPEG for web stream
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if ret:
                return jpeg.tobytes()
            return None

    def save_photo(self):
        with self.lock:
            if self.last_frame is not None:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"Photo_{ts}.jpg"
                filepath = os.path.join(PHOTO_DIR, filename)
                cv2.imwrite(filepath, self.last_frame)
                return filename, filepath
            return None, None

    def start_recording(self):
        with self.lock:
            if self.is_recording:
                return False, "Already recording"
            if self.last_frame is None:
                return False, "No camera feed available"
            
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.record_filename = f"Video_{ts}.mp4"
            self.record_path = os.path.join(VIDEO_DIR, self.record_filename)
            
            h, w, _ = self.last_frame.shape
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(self.record_path, fourcc, 20.0, (w, h))
            self.is_recording = True
            self.record_start_time = time.time()
            return True, self.record_filename

    def stop_recording(self):
        with self.lock:
            if not self.is_recording:
                return False, "Not recording"
            
            self.is_recording = False
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
            
            fn = self.record_filename
            fp = self.record_path
            return True, fn

    def get_record_status(self):
        with self.lock:
            if self.is_recording:
                elapsed = int(time.time() - self.record_start_time)
                return True, elapsed, self.record_filename
            return False, 0, ""

    def release(self):
        with self.lock:
            if self.is_recording and self.video_writer is not None:
                self.video_writer.release()
            if self.cap and self.cap.isOpened():
                self.cap.release()

camera = CameraStream()

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📷 Live HD Camera & Video Recorder - Irak Bhai</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, sans-serif; }
        body {
            background-color: #0f111a;
            color: #f1f1f1;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        header {
            width: 100%;
            max-width: 960px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding: 12px 20px;
            background: #1a1d2e;
            border-radius: 12px;
            border: 1px solid #2e3450;
        }
        h1 { font-size: 1.25rem; font-weight: 600; color: #7aa2f7; display: flex; align-items: center; gap: 8px; }
        .badge {
            background: #41a6b522;
            color: #41a6b5;
            border: 1px solid #41a6b566;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .feed-container {
            width: 100%;
            max-width: 960px;
            background: #000;
            border-radius: 16px;
            overflow: hidden;
            border: 2px solid #2e3450;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            position: relative;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 480px;
        }
        img.video-stream {
            width: 100%;
            height: auto;
            max-height: 600px;
            object-fit: contain;
            display: block;
        }
        .rec-indicator {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(235, 59, 90, 0.85);
            color: white;
            padding: 6px 14px;
            border-radius: 30px;
            font-size: 0.9rem;
            font-weight: bold;
            display: none;
            align-items: center;
            gap: 8px;
            animation: blink 1.2s infinite;
        }
        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0.4; }
            100% { opacity: 1; }
        }
        .controls-bar {
            width: 100%;
            max-width: 960px;
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            align-items: center;
            gap: 12px;
            margin-top: 18px;
            padding: 15px 20px;
            background: #1a1d2e;
            border-radius: 12px;
            border: 1px solid #2e3450;
        }
        .btn {
            border: none;
            padding: 12px 22px;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .btn:active { transform: translateY(1px); }
        
        .btn-photo { background: #7aa2f7; color: #0f111a; }
        .btn-photo:hover { background: #89b4fa; }

        .btn-record { background: #f38ba8; color: #11111b; }
        .btn-record:hover { background: #eba0ac; }

        .btn-stop { background: #a6e3a1; color: #11111b; animation: pulse 1.5s infinite; }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(166, 227, 161, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(166, 227, 161, 0); }
            100% { box-shadow: 0 0 0 0 rgba(166, 227, 161, 0); }
        }

        .btn-secondary {
            background: #2e3450;
            color: #c0caf5;
        }
        .btn-secondary:hover { background: #3b4261; }
        
        .toast {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #9ece6a;
            color: #1a1b26;
            padding: 14px 24px;
            border-radius: 8px;
            font-weight: 600;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            z-index: 1000;
        }
        .toast.show { opacity: 1; }
    </style>
</head>
<body>
    <header>
        <h1>🎥 HD Live Camera & Video Studio</h1>
        <div class="badge">🟢 Live Feed (DirectShow)</div>
    </header>

    <div class="feed-container">
        <div id="recIndicator" class="rec-indicator">🔴 REC <span id="recTimer">00:00</span></div>
        <img class="video-stream" src="/video_feed" alt="Live Stream">
    </div>

    <div class="controls-bar">
        <button id="btnRecord" class="btn btn-record" onclick="toggleRecord()">🎥 Start Recording</button>
        <button class="btn btn-photo" onclick="takeSnapshot()">📸 Take Photo</button>
        <button class="btn btn-secondary" onclick="toggleMirror()">🪞 Mirror Mode</button>
        <button class="btn btn-secondary" onclick="openVideosFolder()">🎬 Open Videos Folder</button>
        <button class="btn btn-secondary" onclick="openPhotosFolder()">📂 Open Photos Folder</button>
        <button class="btn btn-secondary" onclick="toggleFullscreen()">⛶ Fullscreen</button>
    </div>

    <div id="toast" class="toast">Action completed!</div>

    <script>
        let isRecording = false;
        let timerInterval = null;

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 3000);
        }

        function formatTime(sec) {
            const m = Math.floor(sec / 60).toString().padStart(2, '0');
            const s = (sec % 60).toString().padStart(2, '0');
            return `${m}:${s}`;
        }

        function toggleRecord() {
            if (!isRecording) {
                fetch('/start_record', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            isRecording = true;
                            document.getElementById('btnRecord').innerText = '⏹️ Stop Recording';
                            document.getElementById('btnRecord').className = 'btn btn-stop';
                            document.getElementById('recIndicator').style.display = 'flex';
                            showToast('🔴 Recording Started: ' + data.filename);
                            
                            let seconds = 0;
                            timerInterval = setInterval(() => {
                                seconds++;
                                document.getElementById('recTimer').innerText = formatTime(seconds);
                            }, 1000);
                        } else {
                            showToast('❌ ' + data.error);
                        }
                    });
            } else {
                fetch('/stop_record', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            isRecording = false;
                            clearInterval(timerInterval);
                            document.getElementById('btnRecord').innerText = '🎥 Start Recording';
                            document.getElementById('btnRecord').className = 'btn btn-record';
                            document.getElementById('recIndicator').style.display = 'none';
                            document.getElementById('recTimer').innerText = '00:00';
                            showToast('✅ Video Saved in Videos folder: ' + data.filename);
                        } else {
                            showToast('❌ Error stopping recording');
                        }
                    });
            }
        }

        function takeSnapshot() {
            fetch('/capture', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('✅ Photo Saved: ' + data.filename);
                    } else {
                        showToast('❌ Failed to capture photo');
                    }
                })
                .catch(err => showToast('Error capturing photo'));
        }

        function toggleMirror() {
            fetch('/toggle_mirror', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    showToast('🪞 Mirror Mode: ' + (data.mirror ? 'ON' : 'OFF'));
                });
        }

        function openVideosFolder() {
            fetch('/open_videos_folder', { method: 'POST' });
        }

        function openPhotosFolder() {
            fetch('/open_folder', { method: 'POST' });
        }

        function toggleFullscreen() {
            const elem = document.querySelector('.feed-container');
            if (!document.fullscreenElement) {
                elem.requestFullscreen().catch(err => alert(err.message));
            } else {
                document.exitFullscreen();
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

def gen_frames():
    while True:
        frame_bytes = camera.get_frame_bytes()
        if frame_bytes is None:
            time.sleep(0.04)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_record', methods=['POST'])
def start_record():
    success, msg = camera.start_recording()
    if success:
        return jsonify({'success': True, 'filename': msg})
    return jsonify({'success': False, 'error': msg})

@app.route('/stop_record', methods=['POST'])
def stop_record():
    success, msg = camera.stop_recording()
    if success:
        return jsonify({'success': True, 'filename': msg})
    return jsonify({'success': False, 'error': msg})

@app.route('/capture', methods=['POST'])
def capture():
    filename, path = camera.save_photo()
    if filename:
        return jsonify({'success': True, 'filename': filename, 'path': path})
    return jsonify({'success': False})

@app.route('/toggle_mirror', methods=['POST'])
def toggle_mirror():
    camera.mirror = not camera.mirror
    return jsonify({'success': True, 'mirror': camera.mirror})

@app.route('/open_videos_folder', methods=['POST'])
def open_videos_folder():
    if os.path.exists(VIDEO_DIR):
        os.startfile(VIDEO_DIR)
    return jsonify({'success': True})

@app.route('/open_folder', methods=['POST'])
def open_folder():
    if os.path.exists(PHOTO_DIR):
        os.startfile(PHOTO_DIR)
    return jsonify({'success': True})

def open_chrome_app():
    time.sleep(0.8)
    if os.path.exists(CHROME_PATH):
        # Open Google Chrome in standalone App mode
        subprocess.Popen([CHROME_PATH, "--app=http://127.0.0.1:5500"])
    else:
        # Fallback to default browser
        import webbrowser
        webbrowser.open("http://127.0.0.1:5500")

if __name__ == '__main__':
    threading.Thread(target=open_chrome_app, daemon=True).start()
    app.run(host='127.0.0.1', port=5500, threaded=True, debug=False)
