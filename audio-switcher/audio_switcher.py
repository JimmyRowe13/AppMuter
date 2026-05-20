"""
Audio Output Device Switcher
Global hotkey to cycle through audio output devices on Windows.
Runs in system tray. Shows tray balloon notification on switch.
"""
import json
import os
import sys
import queue
import threading
import time

import comtypes
import comtypes.client
import keyboard
import pystray
from PIL import Image, ImageDraw
from pycaw.constants import DEVICE_STATE, EDataFlow, ERole
from pycaw.utils import AudioUtilities

# Thread-safe queue for notifications from hotkey thread
_notify_queue = queue.Queue()
# Global reference to the tray icon
_tray_icon = None


# ---------------------------------------------------------------------------
# Audio device helpers
# ---------------------------------------------------------------------------

def get_active_speakers():
    """Return a list of active audio render (output) devices."""
    return AudioUtilities.GetAllDevices(
        EDataFlow.eRender.value, DEVICE_STATE.ACTIVE.value
    )


def get_default_speaker():
    """Return the current default speaker AudioDevice, or None."""
    return AudioUtilities.GetSpeakers()


def switch_to_next_device():
    """Switch to the next active speaker device. Returns the new device name."""
    speakers = get_active_speakers()
    if len(speakers) < 2:
        return None

    current = get_default_speaker()
    current_id = current.id if current else None

    current_idx = -1
    for i, d in enumerate(speakers):
        if d.id == current_id:
            current_idx = i
            break

    next_idx = (current_idx + 1) % len(speakers)
    next_device = speakers[next_idx]

    AudioUtilities.SetDefaultDevice(next_device.id, [ERole.eMultimedia])
    return next_device.FriendlyName


# ---------------------------------------------------------------------------
# Notification (thread-safe via queue)
# ---------------------------------------------------------------------------

def show_toast(title, message):
    """Enqueue a notification to be shown by the main thread."""
    _notify_queue.put((title, message))


# ---------------------------------------------------------------------------
# Hotkey handler (runs in keyboard hook thread)
# ---------------------------------------------------------------------------

def on_hotkey():
    """Handle hotkey press: switch device and enqueue notification."""
    try:
        comtypes.CoInitialize()
        name = switch_to_next_device()
        if name:
            show_toast("Audio Switcher", f"Switched to: {name}")
        else:
            show_toast("Audio Switcher", "No other active output device found")
    except Exception as e:
        show_toast("Audio Switcher", f"Error: {e}")


# ---------------------------------------------------------------------------
# System tray
# ---------------------------------------------------------------------------

def create_tray_icon():
    """Create a 64x64 speaker icon for the system tray."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([8, 20, 24, 44], fill="white")
    draw.polygon([(24, 20), (24, 44), (44, 52), (44, 12)], fill="white")
    for offset in range(0, 12, 5):
        draw.arc([28 + offset, 12 + offset, 56 - offset, 52 - offset],
                 start=300, end=60, fill="white", width=3)
    return img


# Event to signal tray exit
_exit_event = threading.Event()


def on_tray_exit(icon):
    icon.stop()
    _exit_event.set()


def run_tray():
    """Start the system tray icon and process notifications on main thread."""
    global _tray_icon, _exit_event
    _exit_event.clear()

    icon_img = create_tray_icon()
    menu = pystray.Menu(
        pystray.MenuItem("Exit", on_tray_exit),
    )
    _tray_icon = pystray.Icon("audio_switcher", icon_img, "Audio Switcher", menu)

    # Run icon in a background thread so the main thread can poll for
    # notifications from the hotkey callback (which runs in a hook thread).
    _tray_icon.run_detached()

    # Main thread: poll for notifications and exit signal
    while not _exit_event.is_set():
        try:
            while True:
                title, message = _notify_queue.get_nowait()
                _tray_icon.notify(message, title)
        except queue.Empty:
            pass
        time.sleep(0.2)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def get_app_dir():
    """Get the directory where the executable/script resides."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(exe_dir, "config.json")):
            return exe_dir
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))


def load_config():
    """Load hotkey from config.json next to the executable."""
    config_path = os.path.join(get_app_dir(), "config.json")
    default_config = {"hotkey": "ctrl+shift+f12"}
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default_config


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    comtypes.CoInitialize()

    config = load_config()
    hotkey = config.get("hotkey", "ctrl+shift+f12")

    speakers = get_active_speakers()
    print(f"Audio Switcher started. Hotkey: {hotkey}")
    print(f"Active output devices ({len(speakers)}):")
    current = get_default_speaker()
    for s in speakers:
        marker = " [DEFAULT]" if (current and s.id == current.id) else ""
        print(f"  - {s.FriendlyName}{marker}")

    try:
        keyboard.add_hotkey(hotkey, on_hotkey)
        print(f"Hotkey '{hotkey}' registered. Press to switch audio devices.")
    except Exception as e:
        print(f"Failed to register hotkey: {e}")
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None,
            f"Failed to register hotkey '{hotkey}': {e}",
            "Audio Switcher Error",
            0x40000,
        )
        sys.exit(1)

    run_tray()


if __name__ == "__main__":
    main()
