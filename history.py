"""
history.py - Download history (JSON-based, lightweight).

Keeps a record of every download that completed or failed. Shown in the
"Finished" and "Unfinished" virtual categories. Older entries are pruned
after `history_keep_days` days.
"""
import json
import os
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional
from config import CONFIG_DIR

HISTORY_FILE = CONFIG_DIR / "history.json"


class History:
    """Persistent download history."""

    def __init__(self, keep_days: int = 30):
        self.keep_days = keep_days
        self._lock = threading.Lock()
        self._entries: List[Dict] = []
        self._load()

    def _load(self):
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self._entries = json.load(f)
        except Exception as e:
            print(f"[History] load error: {e}")
            self._entries = []

    def _save(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[History] save error: {e}")

    def add(self, url: str, file_name: str, file_path: str,
            file_size: int, status: str, error: str = ""):
        with self._lock:
            self._entries.append({
                "url": url,
                "file_name": file_name,
                "file_path": file_path,
                "file_size": file_size,
                "status": status,
                "error": error,
                "timestamp": time.time(),
            })
            self._prune()
            self._save()

    def remove(self, file_path: str):
        with self._lock:
            self._entries = [e for e in self._entries if e.get("file_path") != file_path]
            self._save()

    def clear(self):
        with self._lock:
            self._entries = []
            self._save()

    def all(self) -> List[Dict]:
        with self._lock:
            return list(self._entries)

    def finished(self) -> List[Dict]:
        with self._lock:
            return [e for e in self._entries if e.get("status") == "Complete"]

    def _prune(self):
        """Remove entries older than keep_days."""
        cutoff = time.time() - self.keep_days * 86400
        self._entries = [e for e in self._entries if e.get("timestamp", 0) >= cutoff]
