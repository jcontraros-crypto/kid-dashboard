"""
Kid Safe Launcher - Manual Lockdown Edition
Run: python kid_launcher.py
Default parent PIN: 1234

This is a kid-safe, fullscreen dashboard for Windows. It launches only approved
apps/websites, blocks common escape key combinations while running, and requires
a parent PIN to exit or configure.
"""

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import Tk, Toplevel, StringVar, BooleanVar, messagebox, filedialog
import tkinter as tk
from tkinter import ttk

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG = {
    "pin_hash": hashlib.sha256("1234".encode("utf-8")).hexdigest(),
    "kid_name": "Kids",
    "lock_fullscreen": True,
    "always_on_top": True,
    "block_escape_keys": True,
    "block_right_click": True,
    "use_edge_app_mode_for_websites": True,
    "theme": {
        "background": "#eaf7ff",
        "card": "#ffffff",
        "primary": "#2563eb",
        "text": "#1f2937",
        "muted": "#64748b",
        "danger": "#dc2626",
    },
    "items": [
        {"name": "PBS Kids", "type": "website", "target": "https://pbskids.org", "emoji": "🌈"},
        {"name": "Khan Academy Kids", "type": "website", "target": "https://learn.khanacademy.org/khan-academy-kids/", "emoji": "📚"},
        {"name": "Paint", "type": "app", "target": "mspaint.exe", "emoji": "🎨"},
    ],
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = json.loads(json.dumps(DEFAULT_CONFIG))
        merged.update(data)
        if "theme" in data:
            merged["theme"].update(data["theme"])
        return merged
    except Exception as e:
        messagebox.showerror("Config error", f"Could not read config.json:\n{e}\n\nA fresh config will be created.")
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))


def find_edge() -> str | None:
    candidates = [
        r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
        r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
        r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        p = Path(os.path.expandvars(c))
        if p.exists():
            return str(p)
    return None


def bring_pid_to_front(pid: int, fullscreen: bool = True) -> None:
    if os.name != "nt" or not pid:
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        SW_RESTORE = 9
        SW_MAXIMIZE = 3
        hwnds = []
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def callback(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            proc_id = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
            if proc_id.value == pid:
                hwnds.append(hwnd)
            return True

        for _ in range(30):
            hwnds.clear()
            EnumWindows(EnumWindowsProc(callback), 0)
            if hwnds:
                break
            time.sleep(0.15)
        for hwnd in hwnds:
            user32.ShowWindow(hwnd, SW_MAXIMIZE if fullscreen else SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
    except Exception:
        pass


class KeyboardBlocker:
    """Blocks common Windows escape shortcuts while this launcher is running.

    This catches Alt+Tab, Alt+Esc, Alt+F4, Ctrl+Esc, and the Windows keys.
    Windows intentionally does not allow normal apps to block Ctrl+Alt+Del.
    """

    def __init__(self):
        self.enabled = False
        self.hooked = False
        self.thread = None
        self._hook = None
        self._proc = None

    def start(self):
        if os.name != "nt" or self.hooked:
            return
        self.enabled = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.enabled = False
        if os.name == "nt" and self._hook:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
        self._hook = None
        self.hooked = False

    def _run(self):
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            WH_KEYBOARD_LL = 13
            WM_KEYDOWN = 0x0100
            WM_SYSKEYDOWN = 0x0104
            VK_TAB = 0x09
            VK_ESCAPE = 0x1B
            VK_F4 = 0x73
            VK_LWIN = 0x5B
            VK_RWIN = 0x5C
            VK_MENU = 0x12  # Alt
            VK_CONTROL = 0x11

            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("vkCode", ctypes.c_ulong),
                    ("scanCode", ctypes.c_ulong),
                    ("flags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
                ]

            LowLevelKeyboardProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)

            def is_down(vk):
                return bool(user32.GetAsyncKeyState(vk) & 0x8000)

            def hook_proc(nCode, wParam, lParam):
                if nCode == 0 and self.enabled and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    vk = kb.vkCode
                    alt = is_down(VK_MENU)
                    ctrl = is_down(VK_CONTROL)
                    blocked = (
                        vk in (VK_LWIN, VK_RWIN) or
                        (alt and vk in (VK_TAB, VK_ESCAPE, VK_F4)) or
                        (ctrl and vk == VK_ESCAPE)
                    )
                    if blocked:
                        return 1
                return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

            self._proc = LowLevelKeyboardProc(hook_proc)
            self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
            self.hooked = bool(self._hook)
            msg = ctypes.wintypes.MSG()
            while self.enabled:
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.01)
        except Exception:
            self.hooked = False


class MouseBlocker:
    """Blocks right-click/context menu mouse actions while the launcher is running.

    This uses a low-level Windows mouse hook so right-click menus are suppressed
    in the launcher and, where Windows permits, in launched child windows too.
    """

    def __init__(self):
        self.enabled = False
        self.hooked = False
        self.thread = None
        self._hook = None
        self._proc = None

    def start(self):
        if os.name != "nt" or self.hooked:
            return
        self.enabled = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.enabled = False
        if os.name == "nt" and self._hook:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
        self._hook = None
        self.hooked = False

    def _run(self):
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            WH_MOUSE_LL = 14
            WM_RBUTTONDOWN = 0x0204
            WM_RBUTTONUP = 0x0205
            WM_RBUTTONDBLCLK = 0x0206
            WM_NCRBUTTONDOWN = 0x00A4
            WM_NCRBUTTONUP = 0x00A5
            WM_NCRBUTTONDBLCLK = 0x00A6

            LowLevelMouseProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)

            def hook_proc(nCode, wParam, lParam):
                if nCode == 0 and self.enabled and wParam in (
                    WM_RBUTTONDOWN,
                    WM_RBUTTONUP,
                    WM_RBUTTONDBLCLK,
                    WM_NCRBUTTONDOWN,
                    WM_NCRBUTTONUP,
                    WM_NCRBUTTONDBLCLK,
                ):
                    return 1
                return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

            self._proc = LowLevelMouseProc(hook_proc)
            self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, kernel32.GetModuleHandleW(None), 0)
            self.hooked = bool(self._hook)
            msg = ctypes.wintypes.MSG()
            while self.enabled:
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.01)
        except Exception:
            self.hooked = False


class PinDialog(Toplevel):
    def __init__(self, parent, title="Parent PIN"):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.geometry("360x190")
        self.resizable(False, False)
        self.configure(bg="white")
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        tk.Label(self, text="Enter parent PIN", font=("Segoe UI", 16, "bold"), bg="white").pack(pady=(22, 8))
        self.pin = StringVar()
        entry = tk.Entry(self, textvariable=self.pin, show="•", font=("Segoe UI", 17), justify="center")
        entry.pack(padx=35, fill="x")
        entry.focus_set()
        btns = tk.Frame(self, bg="white")
        btns.pack(pady=18)
        tk.Button(btns, text="Cancel", command=self.destroy, width=10).pack(side="left", padx=6)
        tk.Button(btns, text="Unlock", command=self.ok, width=10).pack(side="left", padx=6)
        self.bind("<Return>", lambda _e: self.ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.wait_window(self)

    def ok(self):
        self.result = self.pin.get()
        self.destroy()


class KidLauncher:
    def __init__(self):
        self.config = load_config()
        self.root = Tk()
        self.root.title("Kid Safe Launcher")
        self.root.protocol("WM_DELETE_WINDOW", self.ask_exit)
        self.root.bind("<Alt-F4>", lambda e: "break")
        self.root.bind("<Escape>", lambda e: "break")
        self.root.bind("<Control-q>", lambda e: self.ask_exit())
        self.root.bind("<Control-p>", lambda e: self.open_parent_mode())
        self.root.bind("<F12>", lambda e: self.open_parent_mode())
        self.root.bind_all("<KeyPress-Super_L>", lambda e: "break")
        self.root.bind_all("<KeyPress-Super_R>", lambda e: "break")
        self.child_mode = False
        self.active_process = None
        self.return_panel = None
        self.keyboard_blocker = KeyboardBlocker()
        self.mouse_blocker = MouseBlocker()
        self.block_context_menus()
        if self.config.get("block_escape_keys", True):
            self.keyboard_blocker.start()
        if self.config.get("block_right_click", True):
            self.mouse_blocker.start()
        self.apply_window_mode()
        self.build_ui()
        self.create_return_panel()
        self.keep_front()
        self.keep_return_panel_front()

    def block_context_menus(self):
        def block(_event=None):
            return "break"
        for sequence in ("<Button-3>", "<ButtonRelease-3>", "<Shift-F10>", "<KeyPress-Menu>", "<KeyPress-App>"):
            try:
                self.root.bind_all(sequence, block)
            except Exception:
                pass

    def theme(self, key):
        return self.config.get("theme", DEFAULT_CONFIG["theme"]).get(key, DEFAULT_CONFIG["theme"].get(key))

    def apply_window_mode(self):
        self.root.configure(bg=self.theme("background"))
        self.root.attributes("-topmost", bool(self.config.get("always_on_top", True)))
        if bool(self.config.get("lock_fullscreen", True)):
            self.root.attributes("-fullscreen", True)
        else:
            self.root.geometry("1000x700")

    def keep_front(self):
        try:
            # Keep dashboard as the safe background. When no child app is active, keep it in front.
            if not self.child_mode and self.config.get("always_on_top", True):
                self.root.attributes("-topmost", True)
                self.root.lift()
                self.root.focus_force()
        except Exception:
            pass
        self.root.after(1200, self.keep_front)

    def keep_return_panel_front(self):
        try:
            if self.child_mode and self.return_panel:
                self.return_panel.attributes("-topmost", True)
                self.return_panel.lift()
        except Exception:
            pass
        self.root.after(500, self.keep_return_panel_front)

    def create_return_panel(self):
        try:
            if self.return_panel:
                self.return_panel.destroy()
            self.return_panel = Toplevel(self.root)
            self.return_panel.withdraw()
            self.return_panel.overrideredirect(True)
            self.return_panel.attributes("-topmost", True)
            self.return_panel.configure(bg=self.theme("primary"))
            btn = tk.Button(
                self.return_panel,
                text="← Dashboard",
                command=self.return_to_dashboard,
                bg=self.theme("primary"),
                fg="white",
                activebackground=self.theme("primary"),
                activeforeground="white",
                relief="flat",
                padx=12,
                pady=8,
                font=("Segoe UI", 12, "bold"),
                cursor="hand2",
            )
            btn.pack()
        except Exception:
            pass

    def show_return_panel(self):
        if not self.return_panel:
            return
        try:
            self.return_panel.deiconify()
            self.return_panel.geometry("+16+{}".format(max(16, self.root.winfo_screenheight() - 70)))
            self.return_panel.lift()
        except Exception:
            pass

    def hide_return_panel(self):
        try:
            if self.return_panel:
                self.return_panel.withdraw()
        except Exception:
            pass

    def build_ui(self):
        for w in self.root.winfo_children():
            w.destroy()

        bg = self.theme("background")
        text = self.theme("text")
        muted = self.theme("muted")
        primary = self.theme("primary")

        top = tk.Frame(self.root, bg=bg)
        top.pack(fill="x", padx=34, pady=(24, 8))
        tk.Label(top, text=f"Hi {self.config.get('kid_name', 'Kids')}!", font=("Segoe UI", 34, "bold"), bg=bg, fg=text).pack(side="left")
        tk.Button(top, text="Parent", command=self.open_parent_mode, bg=primary, fg="white", relief="flat", padx=18, pady=10, font=("Segoe UI", 12, "bold"), cursor="hand2").pack(side="right")

        tk.Label(self.root, text="Choose something safe to open", font=("Segoe UI", 16), bg=bg, fg=muted).pack(pady=(0, 16))

        grid = tk.Frame(self.root, bg=bg)
        grid.pack(expand=True)

        items = self.config.get("items", [])
        if not items:
            tk.Label(grid, text="No approved apps yet. Use Parent Mode to add some.", font=("Segoe UI", 18), bg=bg, fg=text).pack()
            return

        columns = 3
        for idx, item in enumerate(items):
            card = tk.Frame(grid, bg=self.theme("card"), highlightthickness=1, highlightbackground="#dbeafe")
            r, c = divmod(idx, columns)
            card.grid(row=r, column=c, padx=16, pady=16, sticky="nsew")
            btn = tk.Button(
                card,
                text=f"{item.get('emoji', '⭐')}\n{item.get('name', 'Untitled')}",
                command=lambda it=item: self.launch_item(it),
                width=18,
                height=6,
                bg=self.theme("card"),
                fg=text,
                relief="flat",
                font=("Segoe UI", 18, "bold"),
                cursor="hand2",
                activebackground="#dbeafe",
            )
            btn.pack(padx=10, pady=10)

        bottom = tk.Frame(self.root, bg=bg)
        bottom.pack(fill="x", padx=30, pady=20)
        tk.Label(bottom, text="Manual lockdown mode is on. Parent PIN required to exit.", font=("Segoe UI", 11), bg=bg, fg=muted).pack(side="left")
        tk.Button(bottom, text="Exit", command=self.ask_exit, bg="#ef4444", fg="white", relief="flat", padx=18, pady=9, font=("Segoe UI", 11, "bold"), cursor="hand2").pack(side="right")

    def launch_item(self, item: dict):
        target = item.get("target", "").strip()
        if not target:
            messagebox.showerror("Missing target", "This launcher item does not have a target.")
            return

        self.child_mode = True
        self.hide_return_panel()
        # Dashboard remains fullscreen behind the app/site as a safe background.
        self.root.attributes("-topmost", False)
        self.root.lift()
        self.root.update_idletasks()

        try:
            if item.get("type") == "website":
                edge = find_edge() if self.config.get("use_edge_app_mode_for_websites", True) else None
                if edge:
                    args = [
                        edge,
                        "--kiosk",
                        target,
                        "--edge-kiosk-type=fullscreen",
                        "--start-fullscreen",
                        "--no-first-run",
                        "--disable-features=Translate,msEdgeShoppingAssistantEnabled",
                    ]
                    self.active_process = subprocess.Popen(args)
                else:
                    # Fallback. Less locked down because browser choice is controlled by Windows.
                    self.active_process = subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
            else:
                self.active_process = subprocess.Popen(target, shell=True)

            self.root.after(700, self._after_launch)
            self.root.after(1600, self._after_launch)
        except Exception as e:
            self.child_mode = False
            self.root.attributes("-topmost", True)
            messagebox.showerror("Launch error", f"Could not open:\n{target}\n\n{e}")

    def _after_launch(self):
        if self.active_process and getattr(self.active_process, "pid", None):
            bring_pid_to_front(self.active_process.pid, fullscreen=True)
        self.show_return_panel()

    def return_to_dashboard(self):
        self.child_mode = False
        self.hide_return_panel()
        try:
            self.root.attributes("-topmost", True)
            self.root.attributes("-fullscreen", bool(self.config.get("lock_fullscreen", True)))
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def verify_pin(self, title="Parent PIN") -> bool:
        dlg = PinDialog(self.root, title)
        return bool(dlg.result) and sha(dlg.result) == self.config.get("pin_hash")

    def ask_exit(self):
        self.return_to_dashboard()
        if self.verify_pin("Exit launcher"):
            self.keyboard_blocker.stop()
            self.mouse_blocker.stop()
            self.root.destroy()
        return "break"

    def open_parent_mode(self):
        self.return_to_dashboard()
        if not self.verify_pin("Parent Mode"):
            return "break"
        ParentWindow(self)
        return "break"

    def run(self):
        self.root.mainloop()
        self.keyboard_blocker.stop()
        self.mouse_blocker.stop()


class ParentWindow(Toplevel):
    def __init__(self, app: KidLauncher):
        super().__init__(app.root)
        self.app = app
        self.title("Parent Mode")
        self.geometry("760x560")
        self.configure(bg="white")
        self.transient(app.root)
        self.grab_set()
        self.focus_force()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=12)
        self.items_tab = tk.Frame(nb, bg="white")
        self.settings_tab = tk.Frame(nb, bg="white")
        nb.add(self.items_tab, text="Approved apps/sites")
        nb.add(self.settings_tab, text="Settings")
        self.build_items_tab()
        self.build_settings_tab()

    def build_items_tab(self):
        left = tk.Frame(self.items_tab, bg="white")
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.listbox = tk.Listbox(left, font=("Segoe UI", 12), height=16)
        self.listbox.pack(fill="both", expand=True)
        self.refresh_list()

        right = tk.Frame(self.items_tab, bg="white")
        right.pack(side="right", fill="y", padx=10, pady=10)
        tk.Button(right, text="Add Website", command=lambda: self.edit_item({"type": "website", "emoji": "🌐"}), width=18).pack(pady=5)
        tk.Button(right, text="Add App", command=self.add_app, width=18).pack(pady=5)
        tk.Button(right, text="Edit Selected", command=self.edit_selected, width=18).pack(pady=5)
        tk.Button(right, text="Remove Selected", command=self.remove_selected, width=18).pack(pady=5)
        tk.Button(right, text="Close", command=self.destroy, width=18).pack(pady=(30, 5))

    def refresh_list(self):
        self.listbox.delete(0, "end")
        for item in self.app.config.get("items", []):
            self.listbox.insert("end", f"{item.get('emoji','⭐')}  {item.get('name')}  [{item.get('type')}]  {item.get('target')}")

    def selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def add_app(self):
        path = filedialog.askopenfilename(title="Choose an app", filetypes=[("Programs", "*.exe *.bat *.cmd"), ("All files", "*.*")])
        if path:
            self.edit_item({"type": "app", "target": path, "name": Path(path).stem, "emoji": "🎮"})

    def edit_selected(self):
        idx = self.selected_index()
        if idx is None:
            return
        self.edit_item(dict(self.app.config["items"][idx]), idx)

    def remove_selected(self):
        idx = self.selected_index()
        if idx is None:
            return
        del self.app.config["items"][idx]
        save_config(self.app.config)
        self.refresh_list()
        self.app.build_ui()

    def edit_item(self, item, idx=None):
        win = Toplevel(self)
        win.title("Launcher Item")
        win.geometry("560x300")
        win.configure(bg="white")
        win.transient(self)
        win.grab_set()

        name = StringVar(value=item.get("name", ""))
        typ = StringVar(value=item.get("type", "website"))
        target = StringVar(value=item.get("target", ""))
        emoji = StringVar(value=item.get("emoji", "⭐"))

        form = tk.Frame(win, bg="white")
        form.pack(fill="both", expand=True, padx=20, pady=20)
        for row, (label, var) in enumerate([("Name", name), ("Type", typ), ("Target URL/path", target), ("Emoji", emoji)]):
            tk.Label(form, text=label, bg="white", font=("Segoe UI", 11, "bold")).grid(row=row, column=0, sticky="w", pady=8)
            if label == "Type":
                ttk.Combobox(form, textvariable=var, values=["website", "app"], state="readonly", width=40).grid(row=row, column=1, sticky="ew", pady=8)
            else:
                tk.Entry(form, textvariable=var, font=("Segoe UI", 11), width=44).grid(row=row, column=1, sticky="ew", pady=8)
        form.columnconfigure(1, weight=1)

        def save():
            new_item = {"name": name.get().strip() or "Untitled", "type": typ.get(), "target": target.get().strip(), "emoji": emoji.get().strip() or "⭐"}
            if idx is None:
                self.app.config.setdefault("items", []).append(new_item)
            else:
                self.app.config["items"][idx] = new_item
            save_config(self.app.config)
            self.refresh_list()
            self.app.build_ui()
            win.destroy()

        tk.Button(win, text="Save", command=save, width=12).pack(side="right", padx=20, pady=16)
        tk.Button(win, text="Cancel", command=win.destroy, width=12).pack(side="right", pady=16)

    def build_settings_tab(self):
        cfg = self.app.config
        bg = "white"
        frame = tk.Frame(self.settings_tab, bg=bg)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        kid_name = StringVar(value=cfg.get("kid_name", "Kids"))
        lock_full = BooleanVar(value=cfg.get("lock_fullscreen", True))
        topmost = BooleanVar(value=cfg.get("always_on_top", True))
        block_keys = BooleanVar(value=cfg.get("block_escape_keys", True))
        block_right = BooleanVar(value=cfg.get("block_right_click", True))
        edge_mode = BooleanVar(value=cfg.get("use_edge_app_mode_for_websites", True))
        new_pin = StringVar()

        rows = [
            ("Kid name", tk.Entry(frame, textvariable=kid_name, width=34)),
            ("Fullscreen launcher", tk.Checkbutton(frame, variable=lock_full, bg=bg)),
            ("Keep dashboard on top", tk.Checkbutton(frame, variable=topmost, bg=bg)),
            ("Block escape keys", tk.Checkbutton(frame, variable=block_keys, bg=bg)),
            ("Block right-click menus", tk.Checkbutton(frame, variable=block_right, bg=bg)),
            ("Use Edge kiosk mode for websites", tk.Checkbutton(frame, variable=edge_mode, bg=bg)),
            ("New PIN (leave blank to keep)", tk.Entry(frame, textvariable=new_pin, show="•", width=34)),
        ]
        for i, (label, widget) in enumerate(rows):
            tk.Label(frame, text=label, bg=bg, font=("Segoe UI", 11, "bold")).grid(row=i, column=0, sticky="w", pady=10)
            widget.grid(row=i, column=1, sticky="w", pady=10)

        note = (
            "Keyboard blocking catches Alt+Tab, Alt+Esc, Alt+F4, Ctrl+Esc, and Windows keys. Right-click blocking suppresses context menus where Windows permits. "
            "Windows does not allow normal apps to block Ctrl+Alt+Del. For maximum safety, use a standard child Windows account."
        )
        tk.Label(frame, text=note, wraplength=560, justify="left", bg=bg, fg="#64748b", font=("Segoe UI", 10)).grid(row=6, column=0, columnspan=2, sticky="w", pady=(16, 8))

        def save_settings():
            cfg["kid_name"] = kid_name.get().strip() or "Kids"
            cfg["lock_fullscreen"] = bool(lock_full.get())
            cfg["always_on_top"] = bool(topmost.get())
            cfg["block_escape_keys"] = bool(block_keys.get())
            cfg["block_right_click"] = bool(block_right.get())
            cfg["use_edge_app_mode_for_websites"] = bool(edge_mode.get())
            if new_pin.get().strip():
                cfg["pin_hash"] = sha(new_pin.get().strip())
            save_config(cfg)
            if cfg["block_escape_keys"]:
                self.app.keyboard_blocker.start()
            else:
                self.app.keyboard_blocker.stop()
            if cfg.get("block_right_click", True):
                self.app.mouse_blocker.start()
            else:
                self.app.mouse_blocker.stop()
            self.app.apply_window_mode()
            self.app.build_ui()
            messagebox.showinfo("Saved", "Settings saved.")

        tk.Button(frame, text="Save Settings", command=save_settings, width=16).grid(row=7, column=1, sticky="e", pady=20)


if __name__ == "__main__":
    KidLauncher().run()
