# Desktop Camera App & Small Popup PiP Camera 📷

A high-performance Windows desktop camera toolkit featuring an **Always-On-Top Half-Inch Mini Floating Camera Widget**, an **Interactive Zoom In/Out System**, a **Global F4 Hardware Hotkey Trigger**, a **Full HD Web Camera Studio for Google Chrome**, and **Native DirectShow Camera Viewers**.

---

## 🌟 Key Features

### 0. 🔲 Half-Inch Smart Mini Camera (`src/mini_camera.pyw` / `1_Mini_Floating_Camera.bat`)
- **Half-Inch Miniature Square (0.5 Inch / 70px)**: Compact square preview widget that launches attached directly to the top-middle of the screen (right beneath the physical webcam lens).
- **Auto Video Recording**: Automatically starts recording high-quality `.mp4` video immediately upon launch.
- **Interactive Zoom In / Zoom Out**:
  - Press **`[+]`** or **`[=]`** ➔ Smoothly Zoom In / Enlarge preview window (+25px per step up to 450px).
  - Press **`[-]`** or **`[_]`** ➔ Smoothly Zoom Out / Shrink preview window down to half-inch (65px).
  - Mouse Scroll Wheel ➔ Scroll Up to zoom in, Scroll Down to zoom out.
  - On-screen zoom buttons (`➕` / `➖`) and right-click presets.
- **Always-On-Top & Drag & Drop**: Easily move the widget anywhere across multiple monitors.
- **1-Click Controls**: Snapshot button (`📸` / `Space`), pause/stop recording (`🔴` / `⏹`), and fast exit (`✖` / `F4` / `Esc`).

### 1. ⌨️ Global F4 Hardware Hotkey (`src/hotkey_service.pyw`)
- **System-Wide Instant Trigger**: Wherever you are in Windows, pressing **`[F4]`** instantly pops up the Half-Inch Mini Camera.
- **1-Touch Toggle**: Press `[F4]` to launch and auto-record; press `[F4]` again to safely finalize the recording and close.
- **Permanent Startup**: Pre-configured in Windows Registry Run key and Startup folder.

### 2. 🎥 Full HD Camera Studio (`2_HD_Camera_Studio_Chrome.bat`)
- Launches standalone in **Google Chrome App Mode** (`--app`).
- Live 720p/1080p camera stream powered by OpenCV DirectShow backend.
- Video Recording, Photo Capture, Mirror View, and Fullscreen toggle.

### 3. ⚡ Native DirectShow Window (`3_Native_Direct_Camera_Window.bat`)
- Ultra-low latency native OpenCV window.
- Press `[Space]` to take instant snapshots, press `[Q]` to exit.

---

## 📂 Output Locations
- **Photos Saved To:** `C:\Users\<User>\Pictures\Camera Roll`
- **Videos Saved To:** `C:\Users\<User>\Videos`

---

## 🚀 Controls Summary
- **`[F4]`**: Global Toggle Open / Close & Save
- **`[+]` / `[=]`**: Zoom In (Enlarge Preview)
- **`[-]` / `[_]`**: Zoom Out (Shrink Preview)
- **`[Mouse Wheel]`**: Zoom In / Out
- **`[Space]`**: Instant Photo Snapshot
- **`[Esc]` / `[Q]`**: Close and Finalize Video

---

## 📄 License
MIT License. Created by [IroScript](https://github.com/IroScript).
