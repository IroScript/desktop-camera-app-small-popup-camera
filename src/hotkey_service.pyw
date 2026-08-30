"""
Ultra-Bulletproof Triple-Layer F4 Global Hotkey Daemon for CameraStudio Mini Camera
Author: Antigravity Assistant for Irak Bhai

Features:
- Triple-Engine Global F4 Detection:
    1) Native Hardware State Poller via GetAsyncKeyState(VK_F4 = 0x73)
    2) pynput Low-Level Hook (KeyCode.from_vk(115), Key.f4, name='f4')
    3) keyboard module raw event hook (name='f4', scan_code=62, vk=115)
    4) Win32 RegisterHotKey message loop
- Automatic Debounce (450ms)
- Preserves Alt+F4 for closing windows
- Socket IPC on port 59122 (--stop, --status, --toggle)
- Automatically launches or closes & saves Mini Camera
"""

import os
import sys
import time
import socket
import threading
import subprocess
import ctypes
from ctypes import wintypes

HOTKEY_SERVICE_PORT = 59122
MINI_CAMERA_PORT = 59123

VK_F4 = 0x73
VK_MENU = 0x12  # Alt key
HOTKEY_ID = 101
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MINI_CAMERA_PATH = os.path.join(SCRIPT_DIR, "mini_camera.pyw")
PYTHONW_PATH = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
if not os.path.exists(PYTHONW_PATH):
    PYTHONW_PATH = "pythonw"

# State
running = True
last_trigger_time = 0
trigger_lock = threading.Lock()


def is_mini_camera_running():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        s.connect(('127.0.0.1', MINI_CAMERA_PORT))
        s.sendall(b'PING\n')
        resp = s.recv(1024)
        s.close()
        return b'PONG' in resp or len(resp) > 0
    except Exception:
        return False


def toggle_mini_camera():
    global last_trigger_time
    with trigger_lock:
        now = time.time()
        if now - last_trigger_time < 0.45:
            return "debounced"
        last_trigger_time = now

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        s.connect(('127.0.0.1', MINI_CAMERA_PORT))
        s.sendall(b'TOGGLE\n')
        s.recv(1024)
        s.close()
        return "toggled"
    except Exception:
        # Mini camera is not running, launch it
        subprocess.Popen(
            [PYTHONW_PATH, MINI_CAMERA_PATH],
            cwd=os.path.dirname(SCRIPT_DIR),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return "launched"


def stop_running_service():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(('127.0.0.1', HOTKEY_SERVICE_PORT))
        s.sendall(b'EXIT\n')
        resp = s.recv(1024)
        s.close()
        return True
    except Exception:
        return False


def check_service_status():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(('127.0.0.1', HOTKEY_SERVICE_PORT))
        s.sendall(b'PING\n')
        resp = s.recv(1024)
        s.close()
        return b'PONG' in resp
    except Exception:
        return False


def is_f4_key(key):
    """Accurately identify F4 across all pynput representations"""
    try:
        from pynput import keyboard
        if key == keyboard.Key.f4:
            return True
    except Exception:
        pass
    if getattr(key, 'vk', None) == 115 or getattr(key, 'vk', None) == 0x73:
        return True
    if getattr(key, 'name', None) == 'f4':
        return True
    return False


def setup_pynput_listener():
    try:
        from pynput import keyboard
        alt_pressed = False

        def on_press(key):
            nonlocal alt_pressed
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                alt_pressed = True
                return
            if is_f4_key(key):
                if not alt_pressed:
                    toggle_mini_camera()

        def on_release(key):
            nonlocal alt_pressed
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                alt_pressed = False

        l = keyboard.Listener(on_press=on_press, on_release=on_release)
        l.daemon = True
        l.start()
        return l
    except Exception:
        return None


def setup_keyboard_module_listener():
    try:
        import keyboard
        def kb_hook(e):
            if e.event_type == 'down':
                if e.name == 'f4' or getattr(e, 'scan_code', None) == 62 or getattr(e, 'vk', None) == 115:
                    if not (user32.GetAsyncKeyState(VK_MENU) & 0x8000):
                        toggle_mini_camera()
        keyboard.hook(kb_hook)
        return True
    except Exception:
        return False


def hardware_poll_loop():
    """Direct kernel-level hardware key state polling (0% CPU with 20ms sleep)"""
    prev_down = False
    while running:
        try:
            # Check physical F4 key state
            f4_down = bool(user32.GetAsyncKeyState(VK_F4) & 0x8000)
            alt_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)

            if f4_down and not prev_down and not alt_down:
                toggle_mini_camera()

            prev_down = f4_down
        except Exception:
            pass
        time.sleep(0.02)


def run_daemon():
    global running
    # Enforce single instance
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lock_socket.bind(('127.0.0.1', HOTKEY_SERVICE_PORT))
        lock_socket.listen(5)
    except socket.error:
        # Service is already running
        sys.exit(0)

    main_thread_id = kernel32.GetCurrentThreadId()

    def ipc_listener():
        global running
        while running:
            try:
                lock_socket.settimeout(1.0)
                conn, _ = lock_socket.accept()
                cmd = conn.recv(1024).decode('utf-8', errors='ignore').strip()
                if cmd == 'EXIT':
                    conn.sendall(b'OK\n')
                    conn.close()
                    running = False
                    user32.PostThreadMessageW(main_thread_id, WM_QUIT, 0, 0)
                    break
                elif cmd == 'PING':
                    conn.sendall(b'PONG\n')
                elif cmd == 'TOGGLE':
                    toggle_mini_camera()
                    conn.sendall(b'OK\n')
                conn.close()
            except socket.timeout:
                continue
            except Exception:
                break
        try:
            lock_socket.close()
        except Exception:
            pass

    threading.Thread(target=ipc_listener, daemon=True).start()

    # Layer 1: Hardware Polling Thread (direct kernel state)
    threading.Thread(target=hardware_poll_loop, daemon=True).start()

    # Layer 2: pynput low-level hook
    pynput_listener = setup_pynput_listener()

    # Layer 3: keyboard module hook
    setup_keyboard_module_listener()

    # Layer 4: Win32 RegisterHotKey
    reg_ok = user32.RegisterHotKey(None, HOTKEY_ID, MOD_NOREPEAT, VK_F4)
    if not reg_ok:
        reg_ok = user32.RegisterHotKey(None, HOTKEY_ID, 0, VK_F4)

    class MSG(ctypes.Structure):
        _fields_ = [
            ('hwnd', wintypes.HWND),
            ('message', wintypes.UINT),
            ('wParam', wintypes.WPARAM),
            ('lParam', wintypes.LPARAM),
            ('time', wintypes.DWORD),
            ('pt', wintypes.POINT),
            ('lPrivate', wintypes.DWORD)
        ]

    msg = MSG()
    try:
        while running and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                toggle_mini_camera()
            elif msg.message == WM_QUIT:
                break
    finally:
        if reg_ok:
            user32.UnregisterHotKey(None, HOTKEY_ID)
        if pynput_listener:
            pynput_listener.stop()
        running = False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ('--stop', '-s', 'stop'):
            if stop_running_service():
                print("F4 Hotkey Service stopped successfully.")
            else:
                print("F4 Hotkey Service was not running.")
            sys.exit(0)
        elif arg in ('--status', 'status'):
            if check_service_status():
                print("F4 Hotkey Service is active.")
            else:
                print("F4 Hotkey Service is inactive.")
            sys.exit(0)
        elif arg in ('--toggle', 'toggle'):
            toggle_mini_camera()
            sys.exit(0)

    run_daemon()
