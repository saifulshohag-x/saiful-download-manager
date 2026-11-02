"""
config.py - Configuration for Saiful Download Manager (IDM-clone edition).
Stores settings in ~/.saiful_dm/config.json
"""
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    CONFIG_DIR = Path(os.environ.get("USERPROFILE", Path.home())) / ".saiful_dm"
else:
    CONFIG_DIR = Path.home() / ".saiful_dm"
CONFIG_FILE = CONFIG_DIR / "config.json"

APP_NAME = "Saiful Download Manager"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Saiful Islam"

DEFAULT_CONFIG = {
    # --- Download settings ---
    "download_folder": str(Path.home() / "Downloads"),
    "segments": 16,
    "max_concurrent": 5,
    "speed_limit_kbps": 0,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "timeout": 60,
    "retries": 10,
    "chunk_size": 262144,
    "tcp_nodelay": True,
    "pool_connections": 128,
    "pool_maxsize": 128,
    "auto_start": True,
    # --- Browser integration ---
    "server_port": 9527,
    # --- Theme ---
    "theme": "Dark",
    "appearance": "dark",
    "window_size": "1280x720",
    # --- Scheduler ---
    "scheduler_enabled": False,
    "scheduler_start": "00:00",
    "scheduler_stop": "23:59",
    "scheduler_days": [1, 2, 3, 4, 5, 6, 7],  # 1=Mon..7=Sun
    "scheduler_auto_shutdown": False,
    # --- Categories (auto-sort downloaded files into subfolders) ---
    "categories_enabled": True,
    "category_folders": True,  # auto-create subfolders
    # --- Clipboard monitor ---
    "clipboard_monitor": True,
    # --- System tray ---
    "minimize_to_tray": True,
    # --- Sounds ---
    "sound_on_complete": True,
    "sound_on_error": False,
    # --- History ---
    "history_keep_days": 30,
    # --- Speed graph ---
    "show_speed_graph": True,
    # --- Antivirus scan ---
    "antivirus_scan": False,
    # --- Video grabber (yt-dlp) ---
    "video_default_format": "best",
    # --- Mark first-run done ---
    "first_run_done": False,
    "extensions_installed": False,
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
        except Exception as e:
            print(f"[Config] load error: {e}")
        try:
            os.makedirs(self._data["download_folder"], exist_ok=True)
        except Exception:
            pass

    def save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] save error: {e}")

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self.save()

    def update(self, mapping):
        self._data.update(mapping)
        self.save()

    def as_dict(self):
        return dict(self._data)


config = Config()
