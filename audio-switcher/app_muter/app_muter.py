"""
App Muter — Mute the foreground application's audio via global hotkey.
Runs in system tray. Left-click toggles mute. Right-click for settings/exit.
"""
import os
import sys
import queue
import threading

import comtypes
import keyboard
import pystray
from typing import Optional

from common.config_manager import load_config, save_config
from common.tray_icon import create_tray_icon
from common.notifications import OSDOverlay
from app_muter.muter_core import AppMuter
from app_muter.settings_window import SettingsWindow

_osd = OSDOverlay()
_muter = AppMuter()
_tray_icon: Optional[pystray.Icon] = None
_exit_event = threading.Event()
_config = {}
_action_queue = queue.Queue()


def _get_config_dir() -> str:
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(exe_dir, "config.json")):
            return exe_dir
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))


# ---- Callbacks that run in their respective threads ----

def on_hotkey():
    """Keyboard hook thread. Signal main thread; no COM calls here."""
    _action_queue.put("TOGGLE")


def on_tray_menu_settings(icon):
    """Tray menu -> Settings. Signal main thread to open tkinter dialog."""
    _action_queue.put("OPEN_SETTINGS")


def on_tray_menu_toggle(icon):
    """Tray menu -> Toggle. Signal main thread to execute mute toggle."""
    _action_queue.put("TOGGLE")


def on_tray_menu_exit(icon):
    """Tray menu -> Exit. Stops tray and signals main thread directly."""
    icon.stop()
    _exit_event.set()


# ---- Actions executed on the MAIN thread ----

def _execute_toggle():
    try:
        result = _muter.toggle_mute()
        if result["error"]:
            _tray_notify("App Muter", result["error"])
        else:
            status = "MUTED" if result["muted"] else "UNMUTED"
            _tray_notify("App Muter", f"{result['name']}: {status}")
            if _config.get("show_osd", True):
                _osd.show(result["name"], result["muted"])
            if _config.get("auto_unmute_on_focus", False):
                _muter.unmute_last()
            _update_tray_icon(result["muted"])
    except Exception as e:
        _tray_notify("App Muter Error", str(e))


def _open_settings():
    """Open the settings dialog on the MAIN thread (required for tkinter)."""
    config_path = os.path.join(_get_config_dir(), "config.json")
    SettingsWindow(config_path=config_path, on_save_callback=_reload_config).show()


def _tray_notify(title: str, message: str):
    if _tray_icon is not None:
        try:
            _tray_icon.notify(message, title)
        except Exception:
            pass


def _update_tray_icon(muted: bool):
    if _tray_icon is not None:
        try:
            _tray_icon.icon = create_tray_icon(muted)
        except Exception:
            pass


def _reload_config(new_config=None):
    global _config
    if new_config is not None:
        save_config(new_config, os.path.join(_get_config_dir(), "config.json"))
    _config = load_config(os.path.join(_get_config_dir(), "config.json"))
    _reregister_hotkey()


def _reregister_hotkey():
    keyboard.unhook_all_hotkeys()
    hotkey = _config.get("hotkey", "ctrl+shift+f12")
    try:
        keyboard.add_hotkey(hotkey, on_hotkey)
    except Exception:
        pass


# ---- Main entry point ----

def main():
    global _tray_icon, _config
    comtypes.CoInitialize()

    _config = load_config(os.path.join(_get_config_dir(), "config.json"))
    hotkey = _config.get("hotkey", "ctrl+shift+f12")

    try:
        keyboard.add_hotkey(hotkey, on_hotkey)
        print(f"App Muter started. Hotkey: {hotkey}")
    except Exception as e:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None,
            f"Failed to register hotkey '{hotkey}': {e}",
            "App Muter Error",
            0x40010,
        )
        sys.exit(1)

    _handle_startup(_config.get("startup_with_windows", False))

    menu = pystray.Menu(
        pystray.MenuItem("Toggle Mute (Foreground App)", on_tray_menu_toggle, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Settings...", on_tray_menu_settings),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_tray_menu_exit),
    )

    _tray_icon = pystray.Icon(
        "app_muter", create_tray_icon(False), "App Muter", menu
    )

    # Tray runs in background daemon thread. Main thread processes the action queue.
    _tray_icon.run_detached()

    # Main thread event loop: processes toggle + settings requests
    while not _exit_event.is_set():
        try:
            action = _action_queue.get(timeout=0.3)
            if action == "TOGGLE":
                _execute_toggle()
            elif action == "OPEN_SETTINGS":
                _open_settings()
        except queue.Empty:
            pass


def _handle_startup(enable: bool):
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
        )
    except OSError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
    try:
        if enable:
            exe_path = sys.executable
            if getattr(sys, "frozen", False):
                target = exe_path
            else:
                target = f'"{exe_path}" "{os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_muter.py")}"'
            winreg.SetValueEx(key, "AppMuter", 0, winreg.REG_SZ, target)
        else:
            try:
                winreg.DeleteValue(key, "AppMuter")
            except FileNotFoundError:
                pass
    finally:
        winreg.CloseKey(key)


if __name__ == "__main__":
    main()
