"""
Ultra-Responsive Mini Floating Camera Widget with Auto-Record & Global F4 Hotkey
Author: Antigravity Assistant for Irak Bhai
Features:
- Auto Video Recording starts immediately upon opening!
- Global F4 Hotkey & Socket IPC daemon on port 59123
- Single-instance lock (prevents duplicate processes fighting for webcam)
- Dedicated background camera thread (zero UI lag, buttery smooth 30fps)
- Always-On-Top (~1.2 inch square floating widget)
- Drag & Drop anywhere on screen
- 1-Click Video Recording + Photo Capture
- Instant close button (✖) / F4 key with safe video finalize & save
"""

import os
import sys
import time
import socket
import datetime
import threading
import subprocess
import tkinter as tk
import cv2
from PIL import Image, ImageTk
import ctypes
from ctypes import wintypes

HOTKEY_SERVICE_PORT = 59122
MINI_CAMERA_PORT = 59123

VK_F4 = 0x73
HOTKEY_ID = 102
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PHOTO_DIR = os.path.expanduser(r"~\Pictures\Camera Roll")
VIDEO_DIR = os.path.expanduser(r"~\Videos")
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)


class CameraWorker(threading.Thread):
    """Dedicated background thread to read webcam frames without blocking GUI"""
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.cap = None
        self.latest_frame = None
        self.mirror = True
        self.lock = threading.Lock()
        
        # Video recording
        self.is_recording = False
        self.video_writer = None
        self.record_filename = ""
        self.record_path = ""
        self.record_start_time = 0

    def run(self):
        # Open camera with DirectShow backend for 100% hardware compatibility
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    if self.mirror:
                        frame = cv2.flip(frame, 1)
                    
                    with self.lock:
                        self.latest_frame = frame.copy()
                        if self.is_recording and self.video_writer is not None:
                            self.video_writer.write(frame)
                else:
                    time.sleep(0.03)
            else:
                time.sleep(0.1)
            time.sleep(0.01)

        with self.lock:
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def get_frame(self):
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def start_record(self):
        with self.lock:
            if self.is_recording or self.latest_frame is None:
                return False
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.record_filename = f"Mini_Video_{ts}.mp4"
            self.record_path = os.path.join(VIDEO_DIR, self.record_filename)
            h, w, _ = self.latest_frame.shape
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(self.record_path, fourcc, 20.0, (w, h))
            self.is_recording = True
            self.record_start_time = time.time()
            return True

    def stop_record(self):
        with self.lock:
            if not self.is_recording:
                return False
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            return True

    def snap_photo(self):
        with self.lock:
            if self.latest_frame is not None:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(PHOTO_DIR, f"Mini_Photo_{ts}.jpg")
                cv2.imwrite(filename, self.latest_frame)
                return filename
            return None

    def stop(self):
        self.running = False
        with self.lock:
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None


class MiniCameraApp:
    def __init__(self, root, auto_record=True):
        self.root = root
        self.root.title("Mini Camera")
        self.running = True
        self.hotkey_registered = False
        self.server_socket = None

        # Dimensions: 170x170 px square
        self.size = 170
        self.root.geometry(f"{self.size}x{self.size}+{self.root.winfo_screenwidth() - self.size - 30}+50")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#11111b")

        # Auto record flag
        self.auto_record = auto_record
        self.has_auto_started = False

        # Camera Worker
        self.worker = CameraWorker()
        self.worker.start()

        # UI Drag state
        self.drag_x = 0
        self.drag_y = 0

        self._build_ui()
        self._setup_events()
        self._start_ipc_server()
        self._setup_local_hotkey()
        self._render_loop()

    def _build_ui(self):
        # Outer Border Frame
        self.border_frame = tk.Frame(self.root, bg="#3b4261", bd=2)
        self.border_frame.pack(fill="both", expand=True)

        # Video Label
        self.canvas_lbl = tk.Label(self.border_frame, bg="#000000")
        self.canvas_lbl.pack(fill="both", expand=True)

        # Control Bar (Top)
        self.top_bar = tk.Frame(self.border_frame, bg="#181825", height=24)
        self.top_bar.place(relx=0.0, rely=0.0, relwidth=1.0, height=24)

        # Record Button
        self.btn_rec = tk.Button(
            self.top_bar,
            text="🔴 REC",
            font=("Segoe UI", 7, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            activebackground="#eba0ac",
            relief="flat",
            bd=0,
            padx=4,
            pady=0,
            cursor="hand2",
            command=self.toggle_rec
        )
        self.btn_rec.pack(side="left", padx=3, pady=2)

        # Snap Photo Button
        self.btn_snap = tk.Button(
            self.top_bar,
            text="📸",
            font=("Segoe UI", 7, "bold"),
            bg="#89b4fa",
            fg="#11111b",
            activebackground="#b4befe",
            relief="flat",
            bd=0,
            padx=4,
            pady=0,
            cursor="hand2",
            command=self.take_snap
        )
        self.btn_snap.pack(side="left", padx=2, pady=2)

        # Close Button (✖)
        self.btn_close = tk.Button(
            self.top_bar,
            text="✖",
            font=("Segoe UI", 7, "bold"),
            bg="#e06c75",
            fg="#ffffff",
            activebackground="#be5046",
            relief="flat",
            bd=0,
            padx=5,
            pady=0,
            cursor="hand2",
            command=self.close_app
        )
        self.btn_close.pack(side="right", padx=3, pady=2)

        # Context Menu (Right Click)
        self.menu = tk.Menu(self.root, tearoff=0, bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 9))
        self.menu.add_command(label="🔴 Start / Stop Recording", command=self.toggle_rec)
        self.menu.add_command(label="📸 Take Photo", command=self.take_snap)
        self.menu.add_separator()
        self.menu.add_command(label="⌨ Hotkey: [F4] Toggle / Close", state="disabled")
        self.menu.add_command(label="🪞 Toggle Mirror Mode", command=self.toggle_mirror)
        self.menu.add_command(label="🔄 Resize: Small (150px)", command=lambda: self.resize_window(150))
        self.menu.add_command(label="🔄 Resize: Medium (220px)", command=lambda: self.resize_window(220))
        self.menu.add_command(label="🔄 Resize: Large (300px)", command=lambda: self.resize_window(300))
        self.menu.add_separator()
        self.menu.add_command(label="📂 Open Videos Folder", command=lambda: os.startfile(VIDEO_DIR))
        self.menu.add_command(label="📂 Open Photos Folder", command=lambda: os.startfile(PHOTO_DIR))
        self.menu.add_separator()
        self.menu.add_command(label="✖ Exit Mini Camera (F4)", command=self.close_app)

    def _setup_events(self):
        # Dragging
        for widget in (self.canvas_lbl, self.border_frame, self.top_bar):
            widget.bind("<Button-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_motion)
            widget.bind("<Button-3>", lambda e: self.menu.post(e.x_root, e.y_root))

        # Double click video to toggle recording
        self.canvas_lbl.bind("<Double-Button-1>", lambda e: self.toggle_rec())

        # Keyboard shortcuts
        self.root.bind("<F4>", lambda e: self.close_app())
        self.root.bind("<Escape>", lambda e: self.close_app())

    def _start_ipc_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', MINI_CAMERA_PORT))
            self.server_socket.listen(5)
        except socket.error:
            # Socket already bound, let main handle it
            return

        def _ipc_loop():
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    conn, _ = self.server_socket.accept()
                    cmd = conn.recv(1024).decode('utf-8', errors='ignore').strip()
                    if cmd == 'PING':
                        conn.sendall(b'PONG\n')
                    elif cmd in ('TOGGLE', 'CLOSE', 'STOP'):
                        conn.sendall(b'CLOSING\n')
                        conn.close()
                        self.root.after(0, self.close_app)
                        break
                    elif cmd == 'SHOW':
                        conn.sendall(b'SHOWN\n')
                        self.root.after(0, lambda: (
                            self.root.deiconify(),
                            self.root.lift(),
                            self.root.attributes("-topmost", True)
                        ))
                    conn.close()
                except socket.timeout:
                    continue
                except Exception:
                    break

        threading.Thread(target=_ipc_loop, daemon=True).start()

    def _setup_local_hotkey(self):
        """Hardware polling and hotkey listener for F4"""
        def _poll_f4():
            prev_f4 = False
            while self.running:
                try:
                    f4_down = bool(user32.GetAsyncKeyState(VK_F4) & 0x8000)
                    alt_down = bool(user32.GetAsyncKeyState(0x12) & 0x8000)
                    if f4_down and not prev_f4 and not alt_down:
                        self.root.after(0, self.close_app)
                        break
                    prev_f4 = f4_down
                except Exception:
                    pass
                time.sleep(0.02)

        threading.Thread(target=_poll_f4, daemon=True).start()

    def _drag_start(self, event):
        self.drag_x = event.x_root - self.root.winfo_x()
        self.drag_y = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self.drag_x
        y = event.y_root - self.drag_y
        self.root.geometry(f"+{x}+{y}")

    def toggle_rec(self):
        if not self.worker.is_recording:
            if self.worker.start_record():
                self.btn_rec.config(text="⏹ STOP", bg="#a6e3a1")
                self.border_frame.config(bg="#f38ba8")
        else:
            self.worker.stop_record()
            self.btn_rec.config(text="🔴 REC", bg="#f38ba8")
            self.border_frame.config(bg="#3b4261")

    def take_snap(self):
        fn = self.worker.snap_photo()
        if fn:
            # Flash white border feedback
            self.border_frame.config(bg="#ffffff")
            self.root.after(200, lambda: self.border_frame.config(bg="#3b4261" if not self.worker.is_recording else "#f38ba8"))

    def toggle_mirror(self):
        self.worker.mirror = not self.worker.mirror

    def resize_window(self, new_size):
        self.size = new_size
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{self.size}x{self.size}+{x}+{y}")

    def _render_loop(self):
        if not self.running:
            return
        frame = self.worker.get_frame()
        if frame is not None:
            # Auto start recording once first live frame arrives
            if self.auto_record and not self.has_auto_started:
                self.has_auto_started = True
                self.toggle_rec()

            # Center-crop square
            h, w, _ = frame.shape
            min_dim = min(h, w)
            cx = (w - min_dim) // 2
            cy = (h - min_dim) // 2
            square = frame[cy:cy+min_dim, cx:cx+min_dim]

            # Resize to fit window below top bar
            render_size = max(self.size - 6, 80)
            resized = cv2.resize(square, (render_size, render_size), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.canvas_lbl.imgtk = imgtk
            self.canvas_lbl.configure(image=imgtk)

        # Update record button text with duration if recording
        if self.worker.is_recording:
            elapsed = int(time.time() - self.worker.record_start_time)
            m, s = divmod(elapsed, 60)
            self.btn_rec.config(text=f"⏹ {m:02d}:{s:02d}")

        self.root.after(30, self._render_loop)

    def close_app(self):
        if not self.running:
            return
        self.running = False
        if self.hotkey_registered:
            try:
                user32.UnregisterHotKey(None, HOTKEY_ID)
            except Exception:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        self.worker.stop()
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)


def send_toggle_to_running_instance():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(('127.0.0.1', MINI_CAMERA_PORT))
        s.sendall(b'TOGGLE\n')
        s.recv(1024)
        s.close()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Test if another instance is already running
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_sock.bind(('127.0.0.1', MINI_CAMERA_PORT))
        test_sock.close()
    except socket.error:
        # Already running, toggle and exit
        send_toggle_to_running_instance()
        sys.exit(0)

    root = tk.Tk()
    app = MiniCameraApp(root, auto_record=True)
    root.mainloop()
