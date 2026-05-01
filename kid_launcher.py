"""
Kid Safe Launcher
A simple fullscreen Python/Tkinter launcher for Windows that only shows parent-approved apps and websites.

Run: python kid_launcher.py
Default parent PIN: 1234
Change it from Parent Mode after launch.
"""

import json
import os
import sys
import hashlib
import subprocess
import webbrowser
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
    "use_edge_app_mode_for_websites": True,
    "theme": {
        "background": "#eaf7ff",
        "card": "#ffffff",
        "primary": "#2563eb",
        "text": "#1f2937",
        "muted": "#64748b"
    },
    "items": [
        {
            "name": "PBS Kids",
            "type": "website",
            "target": "https://pbskids.org",
            "emoji": "🌈"
        },
        {
            "name": "Khan Academy Kids",
            "type": "website",
            "target": "https://learn.khanacademy.org/khan-academy-kids/",
            "emoji": "📚"
        },
        {
            "name": "Paint",
            "type": "app",
            "target": "mspaint.exe",
            "emoji": "🎨"
        }
    ]
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def find_edge() -> str | None:
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


class PinDialog(Toplevel):
    def __init__(self, parent, title="Parent PIN"):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.geometry("340x180")
        self.resizable(False, False)
        self.configure(bg="#ffffff")
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="Enter parent PIN", font=("Segoe UI", 15, "bold")).pack(pady=(22, 8))
        self.pin = StringVar()
        entry = ttk.Entry(self, textvariable=self.pin, show="•", font=("Segoe UI", 16), justify="center")
        entry.pack(padx=35, fill="x")
        entry.focus_set()

        btns = ttk.Frame(self)
        btns.pack(pady=18)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=6)
        ttk.Button(btns, text="Unlock", command=self.ok).pack(side="left", padx=6)
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
        self.apply_window_mode()
        self.build_ui()
        self.keep_front()

    def theme(self, key):
        return self.config.get("theme", DEFAULT_CONFIG["theme"]).get(key, DEFAULT_CONFIG["theme"][key])

    def apply_window_mode(self):
        self.root.configure(bg=self.theme("background"))
        self.root.attributes("-topmost", bool(self.config.get("always_on_top", True)))
        if bool(self.config.get("lock_fullscreen", True)):
            self.root.attributes("-fullscreen", True)
        else:
            self.root.geometry("1000x700")

    def keep_front(self):
        if self.config.get("always_on_top", True):
            try:
                self.root.lift()
                self.root.focus_force()
            except Exception:
                pass
        self.root.after(2500, self.keep_front)

    def build_ui(self):
        for child in self.root.winfo_children():
            child.destroy()

        bg = self.theme("background")
        text = self.theme("text")
        muted = self.theme("muted")
        primary = self.theme("primary")
        card = self.theme("card")
        self.root.configure(bg=bg)

        top = tk.Frame(self.root, bg=bg)
        top.pack(fill="x", padx=36, pady=(28, 12))

        title = tk.Label(top, text=f"Hi {self.config.get('kid_name', 'Kids')}!", bg=bg, fg=text, font=("Segoe UI", 34, "bold"))
        title.pack(side="left")

        parent_btn = tk.Button(top, text="Parent", command=self.open_parent_mode, bg=primary, fg="white", relief="flat", padx=18, pady=10, font=("Segoe UI", 12, "bold"), cursor="hand2")
        parent_btn.pack(side="right")

        subtitle = tk.Label(self.root, text="Choose something fun and safe to open.", bg=bg, fg=muted, font=("Segoe UI", 17))
        subtitle.pack(anchor="w", padx=40, pady=(0, 18))

        grid = tk.Frame(self.root, bg=bg)
        grid.pack(fill="both", expand=True, padx=36, pady=12)

        items = self.config.get("items", [])
        if not items:
            tk.Label(grid, text="No approved apps or websites yet. Open Parent Mode to add some.", bg=bg, fg=muted, font=("Segoe UI", 18)).pack(pady=80)
            return

        cols = 3
        for idx, item in enumerate(items):
            r, c = divmod(idx, cols)
            grid.grid_columnconfigure(c, weight=1, uniform="col")
            grid.grid_rowconfigure(r, weight=1)
            frame = tk.Frame(grid, bg=card, highlightbackground="#dbeafe", highlightthickness=2)
            frame.grid(row=r, column=c, padx=14, pady=14, sticky="nsew")
            frame.bind("<Button-1>", lambda _e, i=item: self.launch(i))

            emoji = tk.Label(frame, text=item.get("emoji", "⭐"), bg=card, fg=text, font=("Segoe UI Emoji", 44))
            emoji.pack(pady=(28, 8))
            emoji.bind("<Button-1>", lambda _e, i=item: self.launch(i))

            name = tk.Label(frame, text=item.get("name", "Untitled"), bg=card, fg=text, font=("Segoe UI", 20, "bold"), wraplength=260)
            name.pack(pady=(6, 4))
            name.bind("<Button-1>", lambda _e, i=item: self.launch(i))

            kind = "Website" if item.get("type") == "website" else "App"
            tk.Label(frame, text=kind, bg=card, fg=muted, font=("Segoe UI", 12)).pack()

            open_btn = tk.Button(frame, text="Open", command=lambda i=item: self.launch(i), bg=primary, fg="white", relief="flat", padx=25, pady=8, font=("Segoe UI", 12, "bold"), cursor="hand2")
            open_btn.pack(pady=20)

        footer = tk.Label(self.root, text="Parent shortcut: Ctrl+P or F12", bg=bg, fg=muted, font=("Segoe UI", 10))
        footer.pack(side="bottom", pady=8)

    def launch(self, item: dict):
        target = item.get("target", "").strip()
        if not target:
            messagebox.showwarning("Missing target", "This launcher item has no app path or website URL.")
            return
        try:
            if item.get("type") == "website":
                self.launch_website(target)
            else:
                self.launch_app(target)
        except Exception as e:
            messagebox.showerror("Could not open", f"I could not open {item.get('name', 'that item')}:\n{e}")

    def launch_website(self, url: str):
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        edge = find_edge() if self.config.get("use_edge_app_mode_for_websites", True) else None
        if edge:
            # App mode hides the normal browser address bar and makes wandering away harder.
            subprocess.Popen([edge, f"--app={url}", "--no-first-run"])
        else:
            webbrowser.open(url)

    def launch_app(self, target: str):
        # Supports either a full path like C:\\Windows\\System32\\notepad.exe or a command like mspaint.exe.
        subprocess.Popen(target, shell=True)

    def check_pin(self) -> bool:
        d = PinDialog(self.root)
        if d.result is None:
            return False
        if sha(d.result) == self.config.get("pin_hash"):
            return True
        messagebox.showerror("Wrong PIN", "That PIN was not correct.")
        return False

    def ask_exit(self):
        if self.check_pin():
            self.root.destroy()

    def open_parent_mode(self):
        if not self.check_pin():
            return
        ParentWindow(self)

    def run(self):
        self.root.mainloop()


class ParentWindow(Toplevel):
    def __init__(self, app: KidLauncher):
        super().__init__(app.root)
        self.app = app
        self.config = app.config
        self.title("Parent Mode")
        self.geometry("850x610")
        self.transient(app.root)
        self.grab_set()
        self.configure(bg="#ffffff")
        self.build()

    def build(self):
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.items_tab = ttk.Frame(tabs)
        self.settings_tab = ttk.Frame(tabs)
        tabs.add(self.items_tab, text="Allowed Apps & Websites")
        tabs.add(self.settings_tab, text="Settings")
        self.build_items_tab()
        self.build_settings_tab()

    def build_items_tab(self):
        top = ttk.Frame(self.items_tab)
        top.pack(fill="x", pady=8)
        ttk.Button(top, text="Add Website", command=lambda: self.edit_item("website")).pack(side="left", padx=4)
        ttk.Button(top, text="Add App", command=lambda: self.edit_item("app")).pack(side="left", padx=4)
        ttk.Button(top, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=4)
        ttk.Button(top, text="Remove Selected", command=self.remove_selected).pack(side="left", padx=4)
        ttk.Button(top, text="Save & Close", command=self.save_close).pack(side="right", padx=4)

        cols = ("name", "type", "target")
        self.tree = ttk.Treeview(self.items_tab, columns=cols, show="headings", height=18)
        for col, label, width in [("name", "Name", 180), ("type", "Type", 90), ("target", "Target", 480)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True)
        self.refresh_tree()

    def refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for idx, item in enumerate(self.config.get("items", [])):
            self.tree.insert("", "end", iid=str(idx), values=(item.get("name"), item.get("type"), item.get("target")))

    def selected_index(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def edit_selected(self):
        idx = self.selected_index()
        if idx is None:
            messagebox.showinfo("Select one", "Please select an item first.")
            return
        self.edit_item(existing_index=idx)

    def remove_selected(self):
        idx = self.selected_index()
        if idx is None:
            messagebox.showinfo("Select one", "Please select an item first.")
            return
        del self.config["items"][idx]
        self.refresh_tree()

    def edit_item(self, item_type="website", existing_index=None):
        item = None if existing_index is None else self.config["items"][existing_index]
        win = Toplevel(self)
        win.title("Launcher Item")
        win.geometry("610x315")
        win.transient(self)
        win.grab_set()

        typ = StringVar(value=(item or {}).get("type", item_type))
        name = StringVar(value=(item or {}).get("name", ""))
        target = StringVar(value=(item or {}).get("target", ""))
        emoji = StringVar(value=(item or {}).get("emoji", "⭐"))

        form = ttk.Frame(win, padding=16)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=name).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Label(form, text="Emoji").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=emoji).grid(row=1, column=1, sticky="ew", pady=6)
        ttk.Label(form, text="Type").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Combobox(form, textvariable=typ, values=["website", "app"], state="readonly").grid(row=2, column=1, sticky="ew", pady=6)
        ttk.Label(form, text="Website URL or App Path").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(form, textvariable=target).grid(row=3, column=1, sticky="ew", pady=6)
        form.grid_columnconfigure(1, weight=1)

        def browse():
            path = filedialog.askopenfilename(title="Choose app", filetypes=[("Programs", "*.exe *.bat *.cmd"), ("All files", "*.*")])
            if path:
                typ.set("app")
                target.set(path)

        ttk.Button(form, text="Browse for App", command=browse).grid(row=4, column=1, sticky="w", pady=8)

        def save():
            if not name.get().strip() or not target.get().strip():
                messagebox.showerror("Missing info", "Name and target are required.")
                return
            new_item = {"name": name.get().strip(), "type": typ.get(), "target": target.get().strip(), "emoji": emoji.get().strip() or "⭐"}
            if existing_index is None:
                self.config.setdefault("items", []).append(new_item)
            else:
                self.config["items"][existing_index] = new_item
            self.refresh_tree()
            win.destroy()

        ttk.Button(form, text="Cancel", command=win.destroy).grid(row=5, column=0, pady=18)
        ttk.Button(form, text="Save", command=save).grid(row=5, column=1, sticky="e", pady=18)

    def build_settings_tab(self):
        frame = ttk.Frame(self.settings_tab, padding=18)
        frame.pack(fill="both", expand=True)
        self.kid_name = StringVar(value=self.config.get("kid_name", "Kids"))
        self.fullscreen = BooleanVar(value=bool(self.config.get("lock_fullscreen", True)))
        self.topmost = BooleanVar(value=bool(self.config.get("always_on_top", True)))
        self.edge_mode = BooleanVar(value=bool(self.config.get("use_edge_app_mode_for_websites", True)))
        self.new_pin = StringVar()

        ttk.Label(frame, text="Kid display name").grid(row=0, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=self.kid_name).grid(row=0, column=1, sticky="ew", pady=8)
        ttk.Checkbutton(frame, text="Fullscreen lock", variable=self.fullscreen).grid(row=1, column=1, sticky="w", pady=8)
        ttk.Checkbutton(frame, text="Keep launcher always on top", variable=self.topmost).grid(row=2, column=1, sticky="w", pady=8)
        ttk.Checkbutton(frame, text="Open websites in Microsoft Edge app mode", variable=self.edge_mode).grid(row=3, column=1, sticky="w", pady=8)
        ttk.Label(frame, text="New parent PIN").grid(row=4, column=0, sticky="w", pady=8)
        ttk.Entry(frame, textvariable=self.new_pin, show="•").grid(row=4, column=1, sticky="ew", pady=8)
        ttk.Label(frame, text="Leave blank to keep current PIN. Default PIN is 1234.").grid(row=5, column=1, sticky="w", pady=2)
        ttk.Button(frame, text="Save Settings", command=self.save_settings).grid(row=6, column=1, sticky="e", pady=24)
        frame.grid_columnconfigure(1, weight=1)

    def save_settings(self):
        self.config["kid_name"] = self.kid_name.get().strip() or "Kids"
        self.config["lock_fullscreen"] = bool(self.fullscreen.get())
        self.config["always_on_top"] = bool(self.topmost.get())
        self.config["use_edge_app_mode_for_websites"] = bool(self.edge_mode.get())
        if self.new_pin.get().strip():
            self.config["pin_hash"] = sha(self.new_pin.get().strip())
        save_config(self.config)
        self.app.config = self.config
        self.app.apply_window_mode()
        self.app.build_ui()
        messagebox.showinfo("Saved", "Settings saved.")

    def save_close(self):
        save_config(self.config)
        self.app.config = self.config
        self.app.apply_window_mode()
        self.app.build_ui()
        self.destroy()


if __name__ == "__main__":
    KidLauncher().run()
