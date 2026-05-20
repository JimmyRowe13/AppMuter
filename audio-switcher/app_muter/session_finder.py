import ctypes
import ctypes.wintypes
from typing import List, Optional

import psutil
from pycaw.utils import AudioUtilities

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 callback type for EnumChildWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)


def get_foreground_window_pid() -> int:
    hwnd = user32.GetForegroundWindow()
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    pid = pid.value

    try:
        proc = psutil.Process(pid)
        if proc.name().lower() == "applicationframehost.exe":
            children = proc.children(recursive=True)
            if children:
                children.sort(key=lambda p: p.memory_info().rss, reverse=True)
                return children[0].pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return pid


def get_foreground_window_handle():
    return user32.GetForegroundWindow()


def find_sessions_for_pid(pid: int, process_name: str = "") -> list:
    """Progressive search for audio sessions related to the foreground app.

    1. Exact PID + descendant process tree
    2. Child windows of the foreground window (catches WebView2/embedded browsers)
    3. Fallback: same executable name
    """
    # Strategy 1: Process tree (PID + children/grandchildren)
    tree_pids = _collect_process_tree(pid)
    sessions = _find_by_pids(tree_pids)
    if sessions:
        return sessions

    # Strategy 2: Child-window PIDs (WebView2, embedded content)
    hwnd = user32.GetForegroundWindow()
    child_pids = _collect_child_window_pids(hwnd)
    child_pids.discard(pid)
    if child_pids:
        sessions = _find_by_pids(child_pids)
        if sessions:
            return sessions

    # Strategy 3: Same executable name (sibling processes)
    if process_name:
        sessions = _find_by_name(process_name)
    return sessions


def _collect_child_window_pids(hwnd) -> set:
    """Enumerate all descendant windows and collect their process IDs."""
    pids = set()

    def callback(child_hwnd, _lparam):
        child_pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(child_hwnd, ctypes.byref(child_pid))
        if child_pid.value:
            pids.add(child_pid.value)
        return True

    user32.EnumChildWindows(hwnd, WNDENUMPROC(callback), 0)
    return pids


def _find_by_pids(pids: set) -> list:
    sessions = []
    for session in AudioUtilities.GetAllSessions():
        try:
            if session.ProcessId in pids and not _is_system_session(session):
                sessions.append(session)
        except Exception:
            continue
    return sessions


def _find_by_name(process_name: str) -> list:
    target = process_name.lower()
    target_exe = target + ".exe" if not target.endswith(".exe") else target

    sessions = []
    for session in AudioUtilities.GetAllSessions():
        try:
            spid = session.ProcessId
            if spid == 0:
                continue
            sproc = psutil.Process(spid)
            sname = sproc.name().lower()
            if (sname == target_exe or sname == target or target in sname) and not _is_system_session(session):
                sessions.append(session)
        except Exception:
            continue
    return sessions


def _collect_process_tree(pid: int) -> set:
    pids = {pid}
    try:
        proc = psutil.Process(pid)
        for child in proc.children(recursive=True):
            pids.add(child.pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return pids


def _is_system_session(session) -> bool:
    """Only PID 0 is the Windows system sounds session."""
    return session.ProcessId == 0


def get_foreground_app_name(pid: int) -> str:
    try:
        proc = psutil.Process(pid)
        return proc.name().replace(".exe", "")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        try:
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if title:
                    return title[:40]
        except Exception:
            pass
        return "Unknown"


def get_diagnostics(pid: int, process_name: str) -> str:
    """Return a diagnostic string listing all audio sessions on the system."""
    lines = [f"Foreground: {process_name} (PID={pid})"]
    lines.append(f"Process tree PIDs: {_collect_process_tree(pid)}")

    hwnd = user32.GetForegroundWindow()
    child_pids = _collect_child_window_pids(hwnd)
    lines.append(f"Child-window PIDs: {child_pids}")

    lines.append("All audio sessions:")
    for s in AudioUtilities.GetAllSessions():
        try:
            spid = s.ProcessId
            sproc = psutil.Process(spid) if spid else None
            sname = sproc.name() if sproc else "System"
            muted = s.SimpleAudioVolume.GetMute() if s.SimpleAudioVolume else "?"
            vol = s.SimpleAudioVolume.GetMasterVolume() if s.SimpleAudioVolume else "?"
            lines.append(f"  PID={spid:6d} {sname:35s} Vol={vol} Muted={muted}")
        except Exception:
            pass
    return "\n".join(lines)
