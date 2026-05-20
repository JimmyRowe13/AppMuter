"""Diagnostic tool: print foreground window info + ALL audio sessions."""
import ctypes, ctypes.wintypes, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psutil
from pycaw.utils import AudioUtilities

user32 = ctypes.windll.user32

# ---- Foreground window ----
hwnd = user32.GetForegroundWindow()
pid = ctypes.wintypes.DWORD()
user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
pid = pid.value

try:
    proc = psutil.Process(pid)
    name = proc.name()
    exe = proc.exe()
    print(f"=== Foreground Window ===")
    print(f"PID: {pid}")
    print(f"Process name: {name}")
    print(f"Exe path: {exe}")

    title_buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, title_buf, 256)
    print(f"Window title: {title_buf.value}")

    print(f"\n=== Process Tree (PID={pid}, name={name}) ===")
    print(f"  [{pid}] {name} (root)")

    if name.lower() == "applicationframehost.exe":
        children = proc.children(recursive=True)
        if children:
            children.sort(key=lambda p: p.memory_info().rss, reverse=True)
            real_proc = children[0]
            pid = real_proc.pid
            name = real_proc.name()
            print(f"  -> UWP real app: [{pid}] {name}")
            proc = real_proc

    for child in proc.children(recursive=True):
        try:
            print(f"  [{child.pid}] {child.name()}")
        except Exception:
            pass

except Exception as e:
    print(f"Error getting process info: {e}")
    name = f"PID_{pid}"

# ---- ALL audio sessions ----
print(f"\n=== All Audio Sessions ===")
all_sessions = AudioUtilities.GetAllSessions()
found_our = []
for s in all_sessions:
    try:
        spid = s.ProcessId
        if spid == 0:
            continue
        sproc = psutil.Process(spid)
        sname = sproc.name()
        muted = s.SimpleAudioVolume.GetMute()
        vol = s.SimpleAudioVolume.GetMasterVolume()
        marker = ""
        if spid == pid:
            marker = " <-- FOREGROUND PID"
            found_our.append(s)
        print(f"  PID={spid:6d}  Name={sname:35s}  Vol={vol:.0%}  Muted={muted}{marker}")
    except Exception:
        pass

print(f"\n=== Result ===")
print(f"Foreground: {name} (PID={pid})")
print(f"Direct PID match sessions: {len(found_our)}")

# Also print all PIDs and names separately for analysis
print(f"\n=== All process names with audio ===")
seen = set()
for s in all_sessions:
    try:
        spid = s.ProcessId
        if spid == 0:
            continue
        sproc = psutil.Process(spid)
        sname = sproc.name().lower()
        if sname not in seen:
            seen.add(sname)
            print(f"  {sname} (PID={spid})")
    except Exception:
        pass
