"""
clipboard_monitor.py - Watch the system clipboard for download URLs.

When the user copies a URL pointing to a downloadable file (based on extension),
this prompts the GUI to ask whether to add it. Like IDM's "Download with IDM"
popup that appears when you copy a URL.
"""
import threading
import time
import re
from typing import Callable, Optional
from urllib.parse import urlparse, unquote
import os

# File extensions we recognize as direct downloads
DOWNLOAD_EXTS = {
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".msi", ".apk", ".dmg", ".deb", ".rpm",
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
    ".iso", ".bin", ".csv", ".json", ".xml",
}


def is_download_url(url: str) -> bool:
    """Heuristic: does this URL look like a direct download link?"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https", "ftp"):
            return False
        path = unquote(parsed.path).lower()
        if not path:
            return False
        _, ext = os.path.splitext(path)
        if ext in DOWNLOAD_EXTS:
            return True
        # Also accept known video/streaming URLs (handled by yt-dlp)
        host = (parsed.netloc or "").lower()
        if any(k in host for k in ["youtube", "youtu.be", "vimeo", "tiktok",
                                    "facebook", "twitter", "x.com"]):
            return True
        return False
    except Exception:
        return False


class ClipboardMonitor:
    """Polls the clipboard every second for new URLs."""

    def __init__(self, on_url: Callable[[str], None]):
        self.on_url = on_url
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_url = ""

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="clipboard")
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                url = self._read_clipboard()
                if url and url != self._last_url and is_download_url(url):
                    self._last_url = url
                    # Fire callback - the GUI decides what to do
                    try:
                        self.on_url(url)
                    except Exception as e:
                        print(f"[Clipboard] callback error: {e}")
            except Exception:
                pass
            self._stop_event.wait(1.5)

    def _read_clipboard(self) -> str:
        """Read text from clipboard. Returns empty string if not available."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            try:
                text = root.clipboard_get()
            finally:
                root.destroy()
            # Take the first line only
            text = (text or "").strip().splitlines()[0] if text else ""
            return text
        except Exception:
            return ""
