import queue
import threading
import tkinter as tk
from typing import Optional, Tuple


class Notifications:
    def __init__(self):
        self._queue = queue.Queue()

    def put(self, title: str, message: str):
        self._queue.put((title, message))

    def get_nowait(self) -> Optional[Tuple[str, str]]:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def get(self, timeout: float = 0.2) -> Optional[Tuple[str, str]]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None


class OSDOverlay:
    def __init__(self, duration_ms: int = 1500):
        self._duration_ms = duration_ms
        self._window = None  # type: Optional[tk.Toplevel]
        self._root = None  # type: ignore

    def _ensure_root(self):
        """Create a hidden root window so Toplevel doesn't show a stray 'tk' window."""
        if self._root is not None:
            return
        if tk._default_root is not None:
            self._root = tk._default_root
            return
        self._root = tk.Tk()
        self._root.withdraw()

    def show(self, app_name: str, muted: bool):
        def _build():
            self._ensure_root()
            if self._window is not None:
                try:
                    self._window.destroy()
                except Exception:
                    pass

            win = tk.Toplevel(self._root)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.configure(bg="#1a1a1a")

            label = tk.Label(
                win,
                text=f"{app_name}  {'[MUTED]' if muted else '[UNMUTED]'}",
                fg="#ffffff" if muted else "#4caf50",
                bg="#1a1a1a",
                font=("Microsoft YaHei UI", 12),
                padx=20,
                pady=12,
            )
            label.pack()

            win.update_idletasks()
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            w = win.winfo_width()
            h = win.winfo_height()
            x = (sw - w) // 2
            y = sh - h - 80
            win.geometry(f"+{x}+{y}")

            win.after(self._duration_ms, lambda: self._hide(win))
            self._window = win

        if threading.current_thread() is threading.main_thread():
            _build()
        else:
            root = tk._default_root
            if root is not None:
                root.after(0, _build)

    def _hide(self, win: tk.Toplevel):
        try:
            win.destroy()
        except Exception:
            pass
        if self._window is win:
            self._window = None
