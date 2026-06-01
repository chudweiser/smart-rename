"""
Smart Rename - Tray app that auto-renames images using local AI (llava via Ollama).
Watches user-selected folders. Fully private, no internet required.
"""

import os
import sys
import time
import base64
import re
import json
import threading
import queue
import requests
import io
from pathlib import Path
from PIL import Image

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import pystray
    from pystray import MenuItem, Menu
    from PIL import ImageDraw
    import watchdog.observers
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("Missing dependencies. Run:  pip install -r requirements.txt")
    sys.exit(1)

# ── Constants ─────────────────────────────────────────────────────────────────

OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "llava"
PROMPT      = (
    "Describe this image in a short phrase suitable for a filename. "
    "Reply with only the phrase, no punctuation, no quotes."
)
IMAGE_EXTS  = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
CONFIG_FILE = Path.home() / ".smart-rename-config.json"

DEFAULT_FOLDERS = []
for candidate in [
    Path.home() / "Downloads",
    Path.home() / "Pictures" / "Screenshots",
    Path.home() / "Pictures",
]:
    if candidate.exists():
        DEFAULT_FOLDERS.append(str(candidate))

MAX_LOG = 200  # max lines kept in the log
_ui_queue: queue.Queue = queue.Queue()  # cross-thread UI requests

# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {"folders": DEFAULT_FOLDERS, "enabled": True}

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

# ── Image helpers ─────────────────────────────────────────────────────────────

def wait_for_file_ready(path: Path, timeout: int = 30) -> bool:
    """Wait until file exists, has stable size, and is not locked."""
    prev_size = -1
    stable_count = 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            curr_size = path.stat().st_size
        except FileNotFoundError:
            return False
        except OSError:
            time.sleep(0.5)
            continue
        if curr_size > 0 and curr_size == prev_size:
            stable_count += 1
        else:
            stable_count = 0
            prev_size = curr_size
        if stable_count >= 2:
            try:
                with open(path, 'rb'):
                    pass
                return True
            except OSError:
                stable_count = 0
        time.sleep(0.5)
    return False

def to_jpg_bytes(path: Path) -> bytes:
    with Image.open(path) as img:
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

def describe_image(path: Path) -> str | None:
    try:
        jpg_bytes = to_jpg_bytes(path)
        b64 = base64.b64encode(jpg_bytes).decode()
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": PROMPT,
            "images": [b64],
            "stream": False,
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        return None

def make_filename(description: str, original: Path) -> Path:
    name = description.lower()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    name = name[:60].strip("_") or "image"
    ext  = original.suffix.lower()
    new  = original.parent / f"{name}{ext}"
    counter = 1
    while new.exists() and new != original:
        new = original.parent / f"{name}_{counter}{ext}"
        counter += 1
    return new

# ── File watcher ──────────────────────────────────────────────────────────────

class ImageHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self._processing = set()   # paths currently being processed
        self._done = set()         # paths already renamed (by original path)
        self._lock = threading.Lock()

    def _claim(self, path: Path) -> bool:
        """Return True if we should process this path, False if already handled."""
        key = str(path)
        with self._lock:
            if key in self._processing or key in self._done:
                return False
            self._processing.add(key)
            return True

    def _release(self, path: Path, renamed_to: Path | None = None):
        key = str(path)
        with self._lock:
            self._processing.discard(key)
            self._done.add(key)
            if renamed_to:
                # Also mark the new name so on_modified events don't reprocess it
                self._done.add(str(renamed_to))

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in IMAGE_EXTS:
            return
        # Delay — browser temp files vanish immediately; real files persist
        threading.Thread(target=self._process_with_delay, args=(path,), daemon=True).start()

    def on_moved(self, event):
        # Browsers write .tmp -> .crdownload -> final image name
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        if dest.suffix.lower() not in IMAGE_EXTS:
            return
        # Mark the source as done so on_created delay thread ignores it
        with self._lock:
            self._done.add(str(Path(event.src_path)))
        threading.Thread(target=self._process, args=(dest,), daemon=True).start()

    def _process_with_delay(self, path: Path):
        time.sleep(2)
        if not path.exists():
            return
        self._process(path)

    def _process(self, path: Path):
        if not self.app.enabled:
            return
        if not self._claim(path):
            return
        self.app.log(f"Detected: {path.name}")
        if not wait_for_file_ready(path):
            self.app.log(f"  ✗ Timed out waiting for file to finish: {path.name}")
            self._release(path)
            return
        if not path.exists():
            self._release(path)
            return
        description = describe_image(path)
        if not description:
            self.app.log(f"  ✗ No description returned for {path.name}")
            self._release(path)
            return
        new_path = make_filename(description, path)
        if new_path == path:
            self.app.log(f"  – Name unchanged: {path.name}")
            self._release(path, path)
            return
        for attempt in range(6):
            try:
                path.rename(new_path)
                self.app.log(f"  ✓ {path.name}  →  {new_path.name}")
                self._release(path, new_path)
                return
            except PermissionError:
                if attempt < 5:
                    time.sleep(0.5)
                else:
                    self.app.log(f"  ✗ Rename failed (file locked): {path.name}")
                    self._release(path)
            except Exception as e:
                self.app.log(f"  ✗ Rename failed: {e}")
                self._release(path)
                return

# ── Tray icon (simple colored square) ────────────────────────────────────────

def make_tray_icon(enabled: bool) -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (34, 197, 94) if enabled else (156, 163, 175)  # green / gray
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    return img

# ── Main App ──────────────────────────────────────────────────────────────────

class SmartRenameApp:
    def __init__(self):
        self.cfg      = load_config()
        self.enabled  = self.cfg.get("enabled", True)
        self.folders  = self.cfg.get("folders", DEFAULT_FOLDERS)
        self.observer = None
        self.tray     = None
        self.window   = None
        self.log_lines = []
        self._log_lock = threading.Lock()

        self._start_observer()
        self._start_tray()

    # ── Logging ───────────────────────────────────────────────────────────────

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        with self._log_lock:
            self.log_lines.append(line)
            if len(self.log_lines) > MAX_LOG:
                self.log_lines.pop(0)
        if self.window and self.window.winfo_exists():
            self.window.after(0, self.window.refresh_log)

    # ── Watcher control ───────────────────────────────────────────────────────

    def _start_observer(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.observer = watchdog.observers.Observer()
        handler = ImageHandler(self)
        for folder in self.folders:
            p = Path(folder)
            if p.exists():
                self.observer.schedule(handler, str(p), recursive=False)
                self.log(f"Watching: {p}")
            else:
                self.log(f"Folder not found (skipped): {p}")
        self.observer.start()

    def set_enabled(self, val: bool):
        self.enabled = val
        self.cfg["enabled"] = val
        save_config(self.cfg)
        self._update_tray_icon()
        self.log("Resumed." if val else "Paused.")

    def set_folders(self, folders: list):
        self.folders = folders
        self.cfg["folders"] = folders
        save_config(self.cfg)
        self._start_observer()

    # ── Tray ──────────────────────────────────────────────────────────────────

    def _start_tray(self):
        def on_settings(icon, item):
            self._open_window()

        def on_toggle(icon, item):
            self.set_enabled(not self.enabled)

        def on_quit(icon, item):
            icon.stop()
            if self.observer:
                self.observer.stop()
            os._exit(0)

        def toggle_label(item):
            return "Pause" if self.enabled else "Resume"

        menu = Menu(
            MenuItem("Smart Rename", None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(toggle_label, on_toggle),
            MenuItem("Settings / Log", on_settings),
            Menu.SEPARATOR,
            MenuItem("Quit", on_quit),
        )
        self.tray = pystray.Icon(
            "smart-rename",
            make_tray_icon(self.enabled),
            "Smart Rename",
            menu,
        )
        threading.Thread(target=self.tray.run, daemon=True).start()

    def _update_tray_icon(self):
        if self.tray:
            self.tray.icon = make_tray_icon(self.enabled)

    # ── Settings window ───────────────────────────────────────────────────────

    def _open_window(self):
        # Must open tkinter windows on the main thread (required on Windows)
        _ui_queue.put("open_settings")


# ── Settings / Log window ─────────────────────────────────────────────────────

class SettingsWindow(tk.Tk):
    def __init__(self, app: SmartRenameApp):
        super().__init__()
        self.app = app
        self.title("Smart Rename")
        self.resizable(True, True)
        self.minsize(560, 480)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self):
        self.configure(padx=16, pady=16)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        hdr.columnconfigure(0, weight=1)

        tk.Label(hdr, text="Smart Rename", font=("", 16, "bold")).grid(row=0, column=0, sticky="w")

        self.status_var = tk.StringVar(value=self._status_text())
        tk.Label(hdr, textvariable=self.status_var, fg="gray").grid(row=1, column=0, sticky="w")

        btn_frame = tk.Frame(hdr)
        btn_frame.grid(row=0, column=1, rowspan=2, sticky="e")
        self.toggle_btn = tk.Button(btn_frame, text=self._toggle_label(),
                                    command=self._toggle, width=10)
        self.toggle_btn.pack()

        # ── Folders ───────────────────────────────────────────────────────────
        tk.Label(self, text="Watched folders", font=("", 11, "bold")).grid(
            row=1, column=0, sticky="w", pady=(0, 4))

        folder_frame = tk.Frame(self)
        folder_frame.grid(row=1, column=0, sticky="ew", pady=(20, 4))
        folder_frame.columnconfigure(0, weight=1)

        self.folder_list = tk.Listbox(folder_frame, height=5, selectmode=tk.SINGLE)
        self.folder_list.grid(row=0, column=0, sticky="ew")
        for f in self.app.folders:
            self.folder_list.insert(tk.END, f)

        btn_row = tk.Frame(folder_frame)
        btn_row.grid(row=1, column=0, sticky="w", pady=4)
        tk.Button(btn_row, text="+ Add folder", command=self._add_folder).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(btn_row, text="− Remove selected", command=self._remove_folder).pack(side=tk.LEFT)

        # ── Log ───────────────────────────────────────────────────────────────
        tk.Label(self, text="Activity log", font=("", 11, "bold")).grid(
            row=2, column=0, sticky="w", pady=(12, 4))

        log_frame = tk.Frame(self)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.log_text = tk.Text(log_frame, state=tk.DISABLED, wrap=tk.WORD,
                                font=("Courier", 9), bg="#1e1e1e", fg="#d4d4d4",
                                relief=tk.FLAT)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.refresh_log()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _status_text(self):
        state = "Active" if self.app.enabled else "Paused"
        n = len(self.app.folders)
        return f"{state}  ·  {n} folder{'s' if n != 1 else ''} watched"

    def _toggle_label(self):
        return "Pause" if self.app.enabled else "Resume"

    def _toggle(self):
        self.app.set_enabled(not self.app.enabled)
        self.status_var.set(self._status_text())
        self.toggle_btn.config(text=self._toggle_label())

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select folder to watch")
        if folder and folder not in self.app.folders:
            self.app.folders.append(folder)
            self.folder_list.insert(tk.END, folder)
            self.app.set_folders(self.app.folders)
            self.status_var.set(self._status_text())

    def _remove_folder(self):
        sel = self.folder_list.curselection()
        if not sel:
            return
        idx = sel[0]
        self.folder_list.delete(idx)
        self.app.folders.pop(idx)
        self.app.set_folders(self.app.folders)
        self.status_var.set(self._status_text())

    def refresh_log(self):
        with self.app._log_lock:
            lines = list(self.app.log_lines)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, "\n".join(lines))
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Check Ollama
    try:
        r = requests.get("http://localhost:11434", timeout=5)
        if "Ollama" not in r.text:
            raise Exception()
    except Exception:
        # Show a simple error and still start — user may start Ollama later
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Smart Rename",
            "Ollama is not running.\n\nStart it with:\n  ollama serve\n\nThe app will still start — images will fail to rename until Ollama is running."
        )
        root.destroy()

    app = SmartRenameApp()

    # Main thread drives all tkinter windows (required on Windows).
    _settings_window = None
    try:
        while True:
            try:
                msg = _ui_queue.get_nowait()
            except queue.Empty:
                msg = None
            if msg == "open_settings":
                if _settings_window is None or not _settings_window.winfo_exists():
                    _settings_window = SettingsWindow(app)
                    _settings_window.mainloop()
                    _settings_window = None
                else:
                    _settings_window.lift()
            time.sleep(0.05)
    except KeyboardInterrupt:
        if app.observer:
            app.observer.stop()
        print("\nStopped.")
