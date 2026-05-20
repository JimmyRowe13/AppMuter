import json
import os
import sys
import tempfile
from typing import Any, Dict, Optional

DEFAULT_CONFIG: Dict[str, Any] = {
    "hotkey": "ctrl+shift+f12",
    "allowlist": [],
    "blocklist": [],
    "auto_unmute_on_focus": False,
    "show_osd": True,
    "startup_with_windows": False,
}


def get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(exe_dir, "config.json")):
            return exe_dir
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))


def get_config_path(app_dir: Optional[str] = None) -> str:
    if app_dir is None:
        app_dir = get_app_dir()
    return os.path.join(app_dir, "config.json")


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = get_config_path()
    config = dict(DEFAULT_CONFIG)
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            config.update(loaded)
    except Exception:
        pass
    return config


def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> None:
    if config_path is None:
        config_path = get_config_path()
    dirname = os.path.dirname(config_path)
    fd, tmp_path = tempfile.mkstemp(dir=dirname, suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, config_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
