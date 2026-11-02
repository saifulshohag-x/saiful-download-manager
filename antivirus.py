"""
antivirus.py - Optional Windows Defender scan after download completes.

Calls MpCmdRun.exe (Windows Defender command-line) to scan a downloaded file.
Non-Windows platforms or absent Defender simply returns "skipped".
"""
import os
import sys
import subprocess
from typing import Tuple


def scan_file(file_path: str, timeout: int = 60) -> Tuple[bool, str]:
    """Returns (clean, message)."""
    if sys.platform != "win32":
        return (True, "Skipped (non-Windows)")
    if not os.path.exists(file_path):
        return (False, "File not found")
    # Locate MpCmdRun.exe
    candidates = [
        r"C:\Program Files\Windows Defender\MpCmdRun.exe",
        r"C:\ProgramData\Microsoft\Windows Defender\Platform\*\MpCmdRun.exe",
    ]
    exe = None
    for c in candidates:
        if "*" in c:
            # Use glob
            import glob
            matches = sorted(glob.glob(c), reverse=True)
            if matches:
                exe = matches[0]
                break
        elif os.path.exists(c):
            exe = c
            break
    if not exe:
        return (True, "Defender not found, skipped")
    try:
        result = subprocess.run(
            [exe, "-Scan", "-ScanType", "3", "-File", file_path],
            capture_output=True, timeout=timeout, text=True
        )
        # Exit code 0 = clean, 2 = threat found
        if result.returncode == 0:
            return (True, "Clean")
        elif result.returncode == 2:
            return (False, "Threat detected!")
        else:
            return (True, f"Skipped (code {result.returncode})")
    except subprocess.TimeoutExpired:
        return (True, "Scan timed out, skipped")
    except Exception as e:
        return (True, f"Scan error: {e}")
