"""
Ultra-Responsive Mini Floating Camera Widget (Half-Inch Square, Top-Middle Attached, Instant Hardware Zoom In/Out)
Author: Antigravity Assistant for Irak Bhai

Features:
- Half-inch square initial size (~70x70px), attached to top-middle of screen directly below webcam
- Instant Hardware Zoom In / Zoom Out via [+] / [=] and [-] / [_] without requiring mouse click
- Force foreground focus on launch
- Auto Video Recording starts immediately upon opening
- Always-On-Top floating widget with drag & drop
- 1-Click Snapshot (📸) + Video Recording Toggle (🔴)
- Global F4 Hotkey + IPC daemon on port 59123
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

# Windows Virtual Key Codes
VK_F4 = 0x73          # F4
VK_ESCAPE = 0x1B      # Esc
VK_OEM_PLUS = 0xBB    # [+] / [=] key
VK_OEM_MINUS = 0xBD   # [-] / [_] key
VK_ADD = 0x6B         # Numpad [+]
VK_SUBTRACT = 0x6D    # Numpad [-]
VK_MENU = 0x12        # Alt key
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

# Size boundaries
MIN_SIZE = 65    # Half-inch square (~0.5 inch)
MAX_SIZE = 450   # Maximum zoom
ZOOM_STEP = 25   # Step size per zoom in / out


def force_window_focus(root):
    """Force OS-level foreground focus to borderless Tkinter window"""
    try:
        root.update_idletasks()
        hwnd = root.winfo_id()
        parent = user32.GetParent(hwnd)
        if parent:
            hwnd = parent
        
        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
        cur_thread = kernel32.GetCurrentThreadId()
        
        if fg_thread != cur_thread and fg_thread != 0:
            user32.AttachThreadInput(fg_thread, cur_thread, True)
            user32.SetForegroundWindow(hwnd)
            user32.SetFocus(hwnd)
            user32.SetActiveWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.AttachThreadInput(fg_thread, cur_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)
            user32.SetFocus(hwnd)
            user32.SetActiveWindow(hwnd)
            user32.BringWindowToTop(hwnd)
    except Exception:
        pass
    root.lift()
    root.attributes("-topmost", True)
    root.focus_force()


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

        # Start with half-inch square size (~70px)
        self.size = 70
        screen_w = self.root.winfo_screenwidth()
        # Position directly at top-center (below webcam lens)
        init_x = (screen_w - self.size) // 2
        init_y = 0

        self.root.geometry(f"{self.size}x{self.size}+{init_x}+{init_y}")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#11111b")

        # Auto record flag
        self.auto_record = auto_record
        self.has_auto_started = False

        # Camera Worker
        self.worker = CameraWorker()
        self.worker.start()

        # UI Drag & Zoom state
        self.drag_x = 0
        self.drag_y = 0
        self.hovered = False
        self.last_hardware_zoom_time = 0

        self._build_ui()
        self._setup_events()
        self._start_ipc_server()
        self._setup_hardware_listener()
        
        # Force OS-level focus immediately on launch
        self.root.after(50, lambda: force_window_focus(self.root))
        self.root.after(150, lambda: self.canvas_lbl.focus_set())

        self._render_loop()

    def _build_ui(self):
        # Outer Border Frame
        self.border_frame = tk.Frame(self.root, bg="#3b4261", bd=2)
        self.border_frame.pack(fill="both", expand=True)

        # Video Label
        self.canvas_lbl = tk.Label(self.border_frame, bg="#000000", cursor="hand2")
        self.canvas_lbl.pack(fill="both", expand=True)

        # Control Bar for larger sizes (hidden at half-inch, visible at size > 90)
        self.top_bar = tk.Frame(self.border_frame, bg="#181825", height=22)
        
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
            padx=3,
            pady=0,
            cursor="hand2",
            command=self.toggle_rec
        )
        self.btn_rec.pack(side="left", padx=2, pady=1)

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
            padx=2,
            pady=0,
            cursor="hand2",
            command=self.take_snap
        )
        self.btn_snap.pack(side="left", padx=1, pady=1)

        # Zoom Out Button (-)
        self.btn_zoom_out = tk.Button(
            self.top_bar,
            text="➖",
            font=("Segoe UI", 7, "bold"),
            bg="#313244",
            fg="#cdd6f4",
            activebackground="#45475a",
            relief="flat",
            bd=0,
            padx=3,
            pady=0,
            cursor="hand2",
            command=self.zoom_out
        )
        self.btn_zoom_out.pack(side="left", padx=1, pady=1)

        # Zoom In Button (+)
        self.btn_zoom_in = tk.Button(
            self.top_bar,
            text="➕",
            font=("Segoe UI", 7, "bold"),
            bg="#313244",
            fg="#cdd6f4",
            activebackground="#45475a",
            relief="flat",
            bd=0,
            padx=3,
            pady=0,
            cursor="hand2",
            command=self.zoom_in
        )
        self.btn_zoom_in.pack(side="left", padx=1, pady=1)

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
            padx=4,
            pady=0,
            cursor="hand2",
            command=self.close_app
        )
        self.btn_close.pack(side="right", padx=2, pady=1)

        # Mini overlay close button for half-inch mode
        self.mini_close = tk.Label(
            self.border_frame,
            text="✖",
            font=("Segoe UI", 7, "bold"),
            bg="#e06c75",
            fg="#ffffff",
            cursor="hand2"
        )
        self.mini_close.bind("<Button-1>", lambda e: self.close_app())

        # Mini rec indicator for half-inch mode
        self.mini_rec_dot = tk.Label(
            self.border_frame,
            text="●",
            font=("Segoe UI", 7, "bold"),
            bg="#000000",
            fg="#f38ba8"
        )

        # Context Menu (Right Click)
        self.menu = tk.Menu(self.root, tearoff=0, bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 9))
        self.menu.add_command(label="➕ Zoom In (+ or =)", command=self.zoom_in)
        self.menu.add_command(label="➖ Zoom Out (- or _)", command=self.zoom_out)
        self.menu.add_separator()
        self.menu.add_command(label="🔄 Half-Inch Square (70px)", command=lambda: self.change_size(70))
        self.menu.add_command(label="🔄 Small (130px)", command=lambda: self.change_size(130))
        self.menu.add_command(label="🔄 Medium (200px)", command=lambda: self.change_size(200))
        self.menu.add_command(label="🔄 Large (300px)", command=lambda: self.change_size(300))
        self.menu.add_separator()
        self.menu.add_command(label="🔴 Start / Stop Recording", command=self.toggle_rec)
        self.menu.add_command(label="📸 Take Photo (Space)", command=self.take_snap)
        self.menu.add_command(label="🪞 Toggle Mirror Mode", command=self.toggle_mirror)
        self.menu.add_separator()
        self.menu.add_command(label="📂 Open Videos Folder", command=lambda: os.startfile(VIDEO_DIR))
        self.menu.add_command(label="📂 Open Photos Folder", command=lambda: os.startfile(PHOTO_DIR))
        self.menu.add_separator()
        self.menu.add_command(label="✖ Exit Mini Camera (F4 / Esc)", command=self.close_app)

        self._update_layout()

    def _update_layout(self):
        """Show full top bar when enlarged, hide when half-inch"""
        if self.size > 90:
            self.top_bar.place(relx=0.0, rely=0.0, relwidth=1.0, height=22)
            self.mini_close.place_forget()
            self.mini_rec_dot.place_forget()
        else:
            self.top_bar.place_forget()
            if self.hovered:
                self.mini_close.place(relx=1.0, rely=0.0, anchor="ne", width=14, height=14)
            else:
                self.mini_close.place_forget()
            if self.worker.is_recording:
                self.mini_rec_dot.place(relx=0.0, rely=0.0, anchor="nw", width=14, height=14)
            else:
                self.mini_rec_dot.place_forget()

    def _setup_events(self):
        # Dragging & clicking
        for widget in (self.canvas_lbl, self.border_frame, self.top_bar):
            widget.bind("<Button-1>", self._on_mouse_down)
            widget.bind("<B1-Motion>", self._drag_motion)
            widget.bind("<Button-3>", lambda e: self.menu.post(e.x_root, e.y_root))
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

        # Double click video to toggle recording
        self.canvas_lbl.bind("<Double-Button-1>", lambda e: self.toggle_rec())

        # Mouse wheel zoom in / out
        self.root.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas_lbl.bind("<MouseWheel>", self._on_mouse_wheel)

        # Tkinter keypress listener for +, =, -, _, F4, Esc, Space
        self.root.bind("<Key>", self._on_key_press)
        self.canvas_lbl.bind("<Key>", self._on_key_press)

    def _on_mouse_down(self, event):
        force_window_focus(self.root)
        self.drag_x = event.x_root - self.root.winfo_x()
        self.drag_y = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self.drag_x
        y = event.y_root - self.drag_y
        self.root.geometry(f"+{x}+{y}")

    def _on_enter(self, event):
        self.hovered = True
        self._update_layout()

    def _on_leave(self, event):
        self.hovered = False
        self._update_layout()

    def _on_mouse_wheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def _on_key_press(self, event):
        k = event.keysym.lower()
        char = event.char
        if char in ('+', '=') or k in ('plus', 'equal', 'kp_add'):
            self.zoom_in()
        elif char in ('-', '_') or k in ('minus', 'underscore', 'kp_subtract'):
            self.zoom_out()
        elif k in ('f4', 'escape', 'q'):
            self.close_app()
        elif char == ' ':
            self.take_snap()

    def zoom_in(self):
        self.change_size(self.size + ZOOM_STEP)

    def zoom_out(self):
        self.change_size(self.size - ZOOM_STEP)

    def change_size(self, new_size):
        new_size = max(MIN_SIZE, min(MAX_SIZE, new_size))
        if new_size == self.size:
            return

        old_size = self.size
        curr_x = self.root.winfo_x()
        curr_y = self.root.winfo_y()

        # Keep centered horizontally
        new_x = curr_x - (new_size - old_size) // 2
        screen_w = self.root.winfo_screenwidth()
        new_x = max(0, min(screen_w - new_size, new_x))

        self.size = new_size
        self.root.geometry(f"{self.size}x{self.size}+{new_x}+{curr_y}")
        self._update_layout()

    def _start_ipc_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('127.0.0.1', MINI_CAMERA_PORT))
            self.server_socket.listen(5)
        except socket.error:
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
                            force_window_focus(self.root)
                        ))
                    elif cmd == 'ZOOM_IN':
                        conn.sendall(b'OK\n')
                        self.root.after(0, self.zoom_in)
                    elif cmd == 'ZOOM_OUT':
                        conn.sendall(b'OK\n')
                        self.root.after(0, self.zoom_out)
                    conn.close()
                except socket.timeout:
                    continue
                except Exception:
                    break

        threading.Thread(target=_ipc_loop, daemon=True).start()

    def _setup_hardware_listener(self):
        """Dedicated background hardware poller for instant key reaction without mouse click"""
        def _poll_keys():
            prev_f4 = False
            prev_esc = False
            prev_plus = False
            prev_minus = False

            while self.running:
                try:
                    now = time.time()

                    # 1. F4 Hardware Check (Close / Toggle)
                    f4_down = bool(user32.GetAsyncKeyState(VK_F4) & 0x8000)
                    alt_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                    if f4_down and not prev_f4 and not alt_down:
                        self.root.after(0, self.close_app)
                        break
                    prev_f4 = f4_down

                    # 2. Escape Hardware Check (Close)
                    esc_down = bool(user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)
                    if esc_down and not prev_esc:
                        self.root.after(0, self.close_app)
                        break
                    prev_esc = esc_down

                    # 3. Zoom In Hardware Check: [+] / [=] key (0xBB) or Numpad [+] (0x6B)
                    plus_down = bool((user32.GetAsyncKeyState(VK_OEM_PLUS) & 0x8000) or (user32.GetAsyncKeyState(VK_ADD) & 0x8000))
                    if plus_down:
                        if not prev_plus or (now - self.last_hardware_zoom_time > 0.14):
                            self.last_hardware_zoom_time = now
                            self.root.after(0, self.zoom_in)
                    prev_plus = plus_down

                    # 4. Zoom Out Hardware Check: [-] / [_] key (0xBD) or Numpad [-] (0x6D)
                    minus_down = bool((user32.GetAsyncKeyState(VK_OEM_MINUS) & 0x8000) or (user32.GetAsyncKeyState(VK_SUBTRACT) & 0x8000))
                    if minus_down:
                        if not prev_minus or (now - self.last_hardware_zoom_time > 0.14):
                            self.last_hardware_zoom_time = now
                            self.root.after(0, self.zoom_out)
                    prev_minus = minus_down

                except Exception:
                    pass
                time.sleep(0.02)

        threading.Thread(target=_poll_keys, daemon=True).start()

    def toggle_rec(self):
        if not self.worker.is_recording:
            if self.worker.start_record():
                self.btn_rec.config(text="⏹ STOP", bg="#a6e3a1")
                self.border_frame.config(bg="#f38ba8")
                self.mini_rec_dot.config(fg="#f38ba8")
        else:
            self.worker.stop_record()
            self.btn_rec.config(text="🔴 REC", bg="#f38ba8")
            self.border_frame.config(bg="#3b4261")
            self.mini_rec_dot.config(fg="#585b70")
        self._update_layout()

    def take_snap(self):
        fn = self.worker.snap_photo()
        if fn:
            # Flash white border feedback
            self.border_frame.config(bg="#ffffff")
            self.root.after(200, lambda: self.border_frame.config(bg="#3b4261" if not self.worker.is_recording else "#f38ba8"))

    def toggle_mirror(self):
        self.worker.mirror = not self.worker.mirror

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

            # Fit render size based on current window size and top bar
            top_offset = 24 if self.size > 90 else 4
            render_size = max(self.size - top_offset, 40)
            resized = cv2.resize(square, (render_size, render_size), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.canvas_lbl.imgtk = imgtk
            self.canvas_lbl.configure(image=imgtk)

        # Update record button text with duration if recording
        if self.worker.is_recording and self.size > 90:
            elapsed = int(time.time() - self.worker.record_start_time)
            m, s = divmod(elapsed, 60)
            self.btn_rec.config(text=f"⏹ {m:02d}:{s:02d}")

        self.root.after(30, self._render_loop)

    def close_app(self):
        if not self.running:
            return
        self.running = False
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
