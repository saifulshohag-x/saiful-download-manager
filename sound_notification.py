"""
sound_notification.py - Play sounds on download complete/error.

Uses winsound on Windows (no extra deps). On other platforms it just prints
a message. The sounds mimic IDM's behavior.
"""
import sys
import os
from pathlib import Path


def play_complete():
    """Play a pleasant 'download complete' sound."""
    if sys.platform == "win32":
        try:
            import winsound  # type: ignore
            # Use Windows' default 'asterisk' sound (3-note chime)
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return
        except Exception:
            pass
    # Linux/macOS fallback - just print
    print("\a[Sound] Download complete")


def play_error():
    """Play an 'error' sound."""
    if sys.platform == "win32":
        try:
            import winsound  # type: ignore
            winsound.MessageBeep(winsound.MB_ICONHAND)
            return
        except Exception:
            pass
    print("\a[Sound] Download error")


def play_added():
    """Play a short 'download added' click sound."""
    if sys.platform == "win32":
        try:
            import winsound  # type: ignore
            winsound.MessageBeep(winsound.MB_OK)
            return
        except Exception:
            pass
    print("\a[Sound] Download added")
