"""
system_tray.py - System tray icon for Saiful Download Manager.

Lets the user minimize to tray and quickly add URLs, pause/resume all,
or quit. Uses pystray.
"""
import threading
from typing import Callable, Optional

# pystray eagerly tries to connect to the display on import (Linux). We must
# wrap the import itself in try/except.
HAS_PYSTRAY = False
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except Exception:
    HAS_PYSTRAY = False


def _make_tray_icon_image(size=64):
    """Create a simple green SDM icon for the system tray."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = size // 8
    d.rounded_rectangle([margin, margin, size - margin, size - margin],
                        radius=size // 5, fill=(15, 90, 60, 255))
    # Down arrow
    cx, cy = size / 2, size * 0.42
    w = size // 6
    h = size // 4
    d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 4], fill="white")
    head = size // 3
    d.polygon([cx - head / 2, cy + h / 4,
               cx + head / 2, cy + h / 4,
               cx, cy + h / 4 + head * 0.7], fill="white")
    return img


class SystemTray:
    """Manages a pystray tray icon. Calls back into the GUI on user actions."""

    def __init__(self,
                 on_show: Callable,
                 on_add_url: Callable,
                 on_pause_all: Callable,
                 on_resume_all: Callable,
                 on_quit: Callable):
        self.on_show = on_show
        self.on_add_url = on_add_url
        self.on_pause_all = on_pause_all
        self.on_resume_all = on_resume_all
        self.on_quit = on_quit
        self._icon: Optional[object] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if not HAS_PYSTRAY or self._icon is not None:
            return
        try:
            image = _make_tray_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem("Open Saiful Download Manager",
                                 lambda: self.on_show(), default=True),
                pystray.MenuItem("Add URL...", lambda: self.on_add_url()),
                pystray.MenuItem("Resume All", lambda: self.on_resume_all()),
                pystray.MenuItem("Pause All", lambda: self.on_pause_all()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", lambda: self.on_quit()),
            )
            self._icon = pystray.Icon("SaifulDownloadManager", image,
                                       "Saiful Download Manager", menu)
            self._thread = threading.Thread(target=self._icon.run, daemon=True,
                                            name="tray")
            self._thread.start()
        except Exception as e:
            print(f"[Tray] failed to start: {e}")

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None
            self._thread = None

    def update_tooltip(self, text: str):
        if self._icon:
            try:
                self._icon.title = text
            except Exception:
                pass
