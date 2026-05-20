import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

import keyboard
from ctypes import windll

from common.config_manager import load_config, save_config
from app_muter.session_finder import get_foreground_window_pid, get_foreground_app_name

class SettingsWindow:
    def __init__(self, config_path=None, on_save_callback=None):
        self._config_path = config_path or self._get_default_config_path()
        self._config = load_config(self._config_path)
        self._on_save_callback = on_save_callback
        self._recording = False
        self._root = None

    def _get_default_config_path(self):
        if getattr(sys, "frozen", False):
            return os.path.join(os.path.dirname(sys.executable), "config.json")
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

    # -------------------------------------------------------------------
    # Build & show the window
    # -------------------------------------------------------------------

    def show(self):
        self._root = tk.Tk()
        self._root.title("设置 - App Muter")
        self._root.resizable(False, False)

        try:
            windll.shell32.SetCurrentProcessExplicitAppUserModelID("appmuter.settings")
        except Exception:
            pass

        notebook = ttk.Notebook(self._root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_hotkey_tab(notebook)
        self._build_filter_tab(notebook)
        self._build_behavior_tab(notebook)
        self._build_about_tab(notebook)

        buttons = ttk.Frame(self._root)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="保存", command=self._on_save).pack(side="right", padx=4)
        ttk.Button(buttons, text="取消", command=self._on_cancel).pack(side="right", padx=4)

        self._root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._center_window()
        try:
            if self._root is not None:
                self._root.mainloop()
        finally:
            if self._root is not None:
                try:
                    self._root.destroy()
                except Exception:
                    pass
                self._root = None

    def _center_window(self):
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self._root.geometry(f"+{x}+{y}")

    # -------------------------------------------------------------------
    # Hotkey tab
    # -------------------------------------------------------------------

    def _build_hotkey_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=15)
        notebook.add(tab, text="快捷键")

        ttk.Label(tab, text="当前快捷键：", font=("", 10)).pack(anchor="w")

        self._hotkey_var = tk.StringVar(value=self._config.get("hotkey", "ctrl+shift+f12"))
        self._hotkey_label = ttk.Label(
            tab, textvariable=self._hotkey_var, font=("", 14, "bold"), foreground="#2196f3"
        )
        self._hotkey_label.pack(anchor="w", pady=(4, 12))

        ttk.Button(tab, text="录制新快捷键...", command=self._start_record).pack(anchor="w")
        self._record_status = ttk.Label(tab, text="", foreground="#888888")
        self._record_status.pack(anchor="w", pady=(2, 0))

        ttk.Button(tab, text="清除快捷键", command=self._clear_hotkey).pack(anchor="w", pady=(12, 4))

        ttk.Label(
            tab,
            text="按下你想使用的按键组合。\n"
                 "例如：ctrl+shift+m、alt+f10、ctrl+alt+page down",
            foreground="#666666",
        ).pack(anchor="w", pady=(16, 0))

    def _start_record(self):
        if self._recording:
            return
        self._recording = True
        self._record_status.config(text="请按下快捷键组合...", foreground="#f44336")

        # Temporarily disable the global hotkey so it doesn't interfere
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        # Use tkinter's own key events — runs on the main thread, no conflict
        self._root.bind("<KeyPress>", self._on_key_press)
        self._root.bind("<KeyRelease>", self._on_key_release)
        self._recorded_modifiers = set()
        self._recorded_key = None
        self._root.focus_force()

    def _on_key_press(self, event):
        if not self._recording:
            return
        # Map tkinter modifier state to readable names (Windows tkinter values)
        mods = []
        if event.state & 0x0004:    # Control
            mods.append("ctrl")
        if event.state & 0x0001:    # Shift
            mods.append("shift")
        if event.state & 0x20000:   # Alt (Mod1)
            mods.append("alt")
        if event.state & 0x0040:    # Windows/Super (Mod4)
            mods.append("windows")

        key = event.keysym.lower()
        # Ignore lone modifier presses
        if key in ("control_l", "control_r", "shift_l", "shift_r",
                    "alt_l", "alt_r", "meta_l", "meta_r", "win_l", "win_r"):
            return

        # Build the hotkey string
        if mods:
            hotkey = "+".join(mods + [key])
        else:
            hotkey = key  # single key, keep it anyway

        self._hotkey_var.set(hotkey)
        self._record_status.config(text="已录制：" + hotkey, foreground="#4caf50")
        self._stop_record()

    def _on_key_release(self, event):
        pass  # We finalize on press, so release is a no-op

    def _stop_record(self):
        if not self._recording:
            return
        self._recording = False
        try:
            self._root.unbind("<KeyPress>")
            self._root.unbind("<KeyRelease>")
        except Exception:
            pass
        # Restore the global hotkey
        if self._on_save_callback:
            self._on_save_callback()

    def _clear_hotkey(self):
        self._hotkey_var.set("")

    # -------------------------------------------------------------------
    # App Filter tab
    # -------------------------------------------------------------------

    def _build_filter_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=15)
        notebook.add(tab, text="应用过滤")

        self._filter_mode = tk.StringVar(value="all")
        ttk.Radiobutton(
            tab, text="全部应用生效", variable=self._filter_mode, value="all"
        ).pack(anchor="w")
        ttk.Radiobutton(
            tab, text="白名单模式（仅列表中应用生效）", variable=self._filter_mode,
            value="allowlist"
        ).pack(anchor="w", pady=(4, 0))
        ttk.Radiobutton(
            tab, text="黑名单模式（排除列表中应用）", variable=self._filter_mode,
            value="blocklist"
        ).pack(anchor="w", pady=(4, 8))

        allowlist = self._config.get("allowlist", [])
        blocklist = self._config.get("blocklist", [])
        if blocklist:
            self._filter_mode.set("blocklist")
        elif allowlist:
            self._filter_mode.set("allowlist")

        list_frame = ttk.Frame(tab)
        list_frame.pack(fill="both", expand=True)

        self._filter_listbox = tk.Listbox(list_frame, height=8, width=40)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._filter_listbox.yview)
        self._filter_listbox.config(yscrollcommand=scrollbar.set)
        self._filter_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_frame, text="添加当前应用", command=self._add_foreground_app).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(btn_frame, text="移除选中", command=self._remove_selected).pack(
            side="left"
        )

        self._filter_mode.trace_add("write", self._on_filter_mode_change)
        self._on_filter_mode_change()
        self._populate_list()

    def _on_filter_mode_change(self, *args):
        pass

    def _populate_list(self):
        self._filter_listbox.delete(0, "end")
        mode = self._filter_mode.get()
        items = self._config.get(mode, []) if mode != "all" else []
        for item in items:
            self._filter_listbox.insert("end", item)

    def _add_foreground_app(self):
        try:
            pid = get_foreground_window_pid()
            name = get_foreground_app_name(pid)
        except Exception:
            messagebox.showerror("错误", "无法检测前台应用。")
            return
        mode = self._filter_mode.get()
        if mode == "all":
            self._filter_mode.set("allowlist")
            self._config["allowlist"] = []
        items = self._config.get(mode, [])
        if name.lower() not in [i.lower() for i in items]:
            items.append(name)
            self._config[mode] = items
            self._populate_list()

    def _remove_selected(self):
        sel = self._filter_listbox.curselection()
        if not sel:
            return
        mode = self._filter_mode.get()
        items = self._config.get(mode, [])
        idx = sel[0]
        if idx < len(items):
            del items[idx]
            self._config[mode] = items
            self._populate_list()

    # -------------------------------------------------------------------
    # Behavior tab
    # -------------------------------------------------------------------

    def _build_behavior_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=15)
        notebook.add(tab, text="行为")

        self._osd_var = tk.BooleanVar(value=self._config.get("show_osd", True))
        ttk.Checkbutton(
            tab, text="显示屏幕静音指示器（OSD）", variable=self._osd_var
        ).pack(anchor="w")

        self._auto_unmute_var = tk.BooleanVar(
            value=self._config.get("auto_unmute_on_focus", False)
        )
        ttk.Checkbutton(
            tab, text="切换应用时自动恢复上一个静音",
            variable=self._auto_unmute_var,
        ).pack(anchor="w", pady=(4, 0))

        self._startup_var = tk.BooleanVar(
            value=self._config.get("startup_with_windows", False)
        )
        ttk.Checkbutton(
            tab, text="开机自启", variable=self._startup_var
        ).pack(anchor="w", pady=(4, 0))

    # -------------------------------------------------------------------
    # About tab
    # -------------------------------------------------------------------

    def _build_about_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=15)
        notebook.add(tab, text="关于")

        ttk.Label(tab, text="App Muter", font=("", 14, "bold")).pack(anchor="w")
        ttk.Label(tab, text="v1.0.0", foreground="#888888").pack(anchor="w", pady=(0, 12))

        info = (
            "通过全局快捷键静音 / 恢复当前前台应用的音量。\n"
            "仅影响当前活动程序，不影响其他应用。\n\n"
            "左键点击托盘图标：切换静音\n"
            "右键点击托盘图标：菜单"
        )
        ttk.Label(tab, text=info, justify="left").pack(anchor="w", pady=(0, 12))

        ttk.Button(
            tab, text="恢复默认设置", command=self._reset_defaults
        ).pack(anchor="w")

    # -------------------------------------------------------------------
    # Save / Cancel / Close
    # -------------------------------------------------------------------

    def _on_save(self):
        hotkey = self._hotkey_var.get().strip()
        if not hotkey:
            messagebox.showwarning("无快捷键", "请设置一个快捷键。")
            return

        self._config["hotkey"] = hotkey
        self._config["show_osd"] = self._osd_var.get()
        self._config["auto_unmute_on_focus"] = self._auto_unmute_var.get()
        self._config["startup_with_windows"] = self._startup_var.get()

        mode = self._filter_mode.get()
        if mode == "all":
            self._config["allowlist"] = []
            self._config["blocklist"] = []
        elif mode == "allowlist":
            self._config["blocklist"] = []
        elif mode == "blocklist":
            self._config["allowlist"] = []

        try:
            save_config(self._config, self._config_path)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{e}")
            return

        if self._on_save_callback:
            self._on_save_callback(self._config)

        self._close()

    def _on_cancel(self):
        if self._recording:
            self._stop_record()
        self._close()

    def _close(self):
        if self._root is None:
            return
        self._cleanup()
        try:
            self._root.quit()
        except Exception:
            pass
        try:
            self._root.destroy()
        except Exception:
            pass
        self._root = None

    def _reset_defaults(self):
        if messagebox.askyesno("重置", "确定恢复所有设置到默认值？"):
            self._config = {
                "hotkey": "ctrl+shift+f12",
                "allowlist": [],
                "blocklist": [],
                "auto_unmute_on_focus": False,
                "show_osd": True,
                "startup_with_windows": False,
            }
            self._hotkey_var.set("ctrl+shift+f12")
            self._osd_var.set(True)
            self._auto_unmute_var.set(False)
            self._startup_var.set(False)
            self._filter_mode.set("all")
            self._populate_list()

    def _cleanup(self):
        if self._recording:
            self._stop_record()
