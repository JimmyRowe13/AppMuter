import os
import tempfile
import time
from typing import Dict, List, Optional

from common.config_manager import load_config
from app_muter.session_finder import (
    get_foreground_window_pid,
    find_sessions_for_pid,
    get_foreground_app_name,
    get_diagnostics,
)


class AppMuter:
    def __init__(self):
        self._last_muted_pid: int = 0
        self._last_muted_name: str = ""

    def is_allowed(self, process_name: str) -> bool:
        config = load_config()
        name_lower = process_name.lower()
        allowlist = [a.lower() for a in config.get("allowlist", [])]
        blocklist = [b.lower() for b in config.get("blocklist", [])]

        if blocklist and name_lower in blocklist:
            return False
        if allowlist and name_lower not in allowlist:
            return False
        return True

    def toggle_mute(self) -> dict:
        pid = get_foreground_window_pid()
        name = get_foreground_app_name(pid)

        if not self.is_allowed(name):
            return {"name": name, "muted": False,
                    "error": f"'{name}' excluded by filter"}

        sessions = find_sessions_for_pid(pid, name)
        if not sessions:
            diag = get_diagnostics(pid, name)
            log_path = os.path.join(tempfile.gettempdir(), f"app_muter_diag_{int(time.time())}.txt")
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(diag)
            except Exception:
                log_path = "(write failed)"
            return {"name": name, "muted": False,
                    "error": f"'{name}' (PID={pid}): no session. Log: {log_path}"}

        any_unmuted = any(not self._get_mute(s) for s in sessions)
        new_mute = any_unmuted

        for session in sessions:
            try:
                session.SimpleAudioVolume.SetMute(new_mute, None)
            except Exception:
                continue

        if new_mute:
            self._last_muted_pid = pid
            self._last_muted_name = name

        return {"name": name, "muted": new_mute, "error": None}

    def unmute_last(self):
        if self._last_muted_pid == 0:
            return
        sessions = find_sessions_for_pid(self._last_muted_pid, self._last_muted_name)
        for session in sessions:
            try:
                session.SimpleAudioVolume.SetMute(False, None)
            except Exception:
                pass
        self._last_muted_pid = 0
        self._last_muted_name = ""

    @staticmethod
    def _get_mute(session) -> bool:
        try:
            return bool(session.SimpleAudioVolume.GetMute())
        except Exception:
            return False
