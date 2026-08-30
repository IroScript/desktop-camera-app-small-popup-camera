# Desktop Camera App & Small Popup PiP Camera 📷

A high-performance Windows desktop camera toolkit featuring an **Always-On-Top Mini Floating PiP Camera Widget**, a **Global F4 Hardware Hotkey Trigger**, a **Full HD Web Camera Studio for Google Chrome**, and **Native DirectShow Camera Viewers**.

---

## 🌟 Key Features

### 0. ⌨️ Global F4 Hardware Hotkey (`src/hotkey_service.pyw`)
- **System-Wide Instant Trigger**: Wherever you are in Windows (browser, full-screen apps, games, desktop), pressing **`[F4]`** instantly pops up the Mini Floating Camera widget.
- **Smart 1-Touch Toggle**:
  - Press **`[F4]`** ➔ Launches Mini Camera instantly with automatic high-definition video recording.
  - Press **`[F4]`** again ➔ Safely finalizes the `.mp4` video recording, releases camera hardware, and closes the widget.
- **Triple-Engine Detection**: Powered by kernel-level hardware polling (`GetAsyncKeyState`), low-level keyboard hooks (`pynput`), and raw keyboard hooks (`keyboard`).
- **Zero Resource Consumption**: Runs silently in the background with 0% CPU usage and negligible memory.
- **Permanent Windows Startup**: Automatically starts with Windows boot via both Registry Run key (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) and Startup folder (`CameraStudio_F4.vbs`).

### 1. 🔲 Mini Floating PiP Camera (`src/mini_camera.pyw` / `1_Mini_Floating_Camera.bat`)
- **1-Inch Compact Floating Widget**: Stays **Always-On-Top** of all applications and games.
- **Auto Video Recording**: Automatically starts recording high-quality `.mp4` video immediately upon launch with a live duration timer.
- **Drag & Drop Anywhere**: Easily move the widget anywhere across multiple monitors.
- **1-Click Controls**: Snapshot button (`📸`), pause/stop recording (`⏹`), and fast exit (`✖` / `[F4]`).
- **Right-Click Context Menu**: Resize on the fly (Small: 150px / Medium: 220px / Large: 300px), toggle mirror mode, and quick access to photos/videos folders.
- **Single-Instance Protection & IPC**: Dedicated background thread and socket IPC prevent webcam conflicts.

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

## 🚀 Script Architecture & Launch Files
- `src/hotkey_service.pyw` - Background F4 global hardware hotkey daemon
- `src/mini_camera.pyw` - Core mini floating camera widget with auto-recording
- `0_Start_F4_Global_Hotkey_Service.bat` - Manual launcher for F4 background service
- `Enable_F4_Startup.bat` - Configure F4 service in Windows Startup
- `Disable_F4_Startup.bat` - Remove F4 service from Windows Startup
- `Stop_F4_Hotkey_Service.bat` - Stop running F4 background service
- `1_Mini_Floating_Camera.bat` - Launch Mini Floating Camera directly
- `2_HD_Camera_Studio_Chrome.bat` - Launch HD Camera Studio in Chrome
- `3_Native_Direct_Camera_Window.bat` - Launch Native DirectShow window

---

## 📄 License
MIT License. Created by [IroScript](https://github.com/IroScript).
