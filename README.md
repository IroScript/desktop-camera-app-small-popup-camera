# Desktop Camera App & Small Popup PiP Camera 📷

A high-performance Windows desktop camera toolkit featuring an **Always-On-Top Mini Floating PiP Camera Widget**, a **Full HD Web Camera Studio for Google Chrome**, and **Native DirectShow Camera Viewers**.

---

## 🌟 Key Features

### 1. 🔲 Mini Floating PiP Camera (`1_Mini_Floating_Camera.bat`)
- **1-Inch Compact Floating Widget**: Stays **Always-On-Top** of all applications and games.
- **Auto Video Recording**: Automatically starts recording high-quality `.mp4` video immediately upon launch with a live duration timer.
- **Drag & Drop**: Easily move the widget anywhere across multiple monitors.
- **1-Click Controls**: Snapshot button (`📸`), pause/stop recording (`⏹`), and fast exit (`✖`).
- **Right-Click Context Menu**: Resize on the fly (Small / Medium / Large), toggle mirror mode, and quick access to photos/videos folders.
- **Single-Instance Protection**: Dedicated background thread and socket lock prevent webcam conflicts.

### 2. 🎥 Full HD Camera Studio (`2_HD_Camera_Studio_Chrome.bat`)
- Launches standalone in **Google Chrome App Mode** (`--app`).
- Live 720p/1080p camera stream powered by OpenCV DirectShow backend.
- Video Recording, Photo Capture, Mirror View, and Fullscreen toggle.

### 3. ⚡ Native DirectShow Window (`3_Native_Direct_Camera_Window.bat`)
- Ultra-low latency native OpenCV window.
- Press `[Space]` to take instant snapshots, press `[Q]` to exit.

### 4. 🛠️ Windows Camera Registry Fix (`Fix_Windows_Camera_Registry.reg`)
- Fixes `System.ArgumentException` and splash screen freezes in built-in Windows Camera UWP apps by disabling problematic Frame Server mode.

---

## 📂 Output Locations
- **Photos Saved To:** `C:\Users\<User>\Pictures\Camera Roll`
- **Videos Saved To:** `C:\Users\<User>\Videos`

---

## 🚀 Requirements & Quick Start
- Windows 10 / 11
- Python 3.10+ with `opencv-python`, `pillow`, `flask`
- Double-click any `.bat` launcher to run instantly!

---

## 📄 License
MIT License. Created by [IroScript](https://github.com/IroScript).
