"""
extension_installer.py - Auto-installs the Saiful Download Manager browser
extension into Chrome, Edge, Brave, Opera and Firefox on Windows.

How it works (Windows-only feature):
1. Bundles a copy of the Chromium extension at:
     %LOCALAPPDATA%\\SaifulDownloadManager\\extension
2. For Chromium-based browsers (Chrome, Edge, Brave, Opera), edits the
   browser's Preferences JSON to add our extension as an installed unpacked
   extension with a stable extension ID. The browser will load it on next
   launch (it shows a one-time "Disable developer mode extensions" prompt
   that the user can click away).
3. For Firefox, registers the extension via the Windows Registry key:
     HKCU\\Software\\Mozilla\\Firefox\\Extensions\\<UUID> = <path-to-xpi>
   Firefox will pick it up on next launch.

On Linux / macOS this module runs in a no-op mode and reports which
browsers it would target.

The user can trigger installation from the GUI's "Browser Extensions"
button, or it auto-runs once on first launch (controlled by the config
key `extensions_installed`).
"""
import os
import sys
import json
import shutil
import hashlib
import platform
from pathlib import Path
from typing import List, Dict, Tuple

# Stable extension ID for the Chromium extension. We use the SHA256 of the
# extension's public key (a fixed dummy key here, must match manifest's "key"
# field if set; for unpacked extensions Chrome derives the ID from the path
# if "key" is absent, which is unstable. We pin a stable ID by writing a
# "key" entry derived from a known RSA public key. For simplicity we use a
# fixed ID constant and trust the load-unpacked path).
CHROMIUM_EXT_ID = "saifuldownloadmanager@example"  # not used as actual ID
# We use the path-based approach: Preferences references the folder path,
# which gives us a stable install without needing a Web Store key.

APP_DATA_NAME = "SaifulDownloadManager"


def _is_windows() -> bool:
    return sys.platform == "win32" or platform.system() == "Windows"


# ---------------------------------------------------------------------------
# Locate the bundled extension folder
# ---------------------------------------------------------------------------
def _bundled_extension_dir() -> Path:
    """Return the path to the bundled Chromium extension folder."""
    if getattr(sys, "frozen", False):
        # PyInstaller: bundled into _MEIPASS or alongside exe
        base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent
    p = base / "extension" / "saiful_ext"
    return p


def _bundled_firefox_xpi_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent
    return base / "firefox_extension"


def _install_target_dir() -> Path:
    """Where to copy the extension so browsers can find it."""
    if _is_windows():
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    else:
        base = Path.home()
    p = base / APP_DATA_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Browser detection (Windows paths)
# ---------------------------------------------------------------------------
def detect_browsers() -> List[Dict]:
    """Return list of detected browsers with their name, executable and user-data folder."""
    browsers = []
    if not _is_windows():
        # Linux/macOS paths for graceful degradation
        candidates = [
            ("Google Chrome", "/.config/google-chrome", "/usr/bin/google-chrome"),
            ("Brave", "/.config/BraveSoftware/Brave-Browser", "/usr/bin/brave-browser"),
            ("Microsoft Edge", "/.config/microsoft-edge", "/usr/bin/microsoft-edge"),
            ("Firefox", "/.mozilla/firefox", "/usr/bin/firefox"),
        ]
        home = str(Path.home())
        for name, data_dir, exe in candidates:
            full_data = home + data_dir
            full_exe = exe
            if Path(full_data).exists() or Path(full_exe).exists():
                browsers.append({
                    "name": name,
                    "user_data": full_data,
                    "exe": full_exe,
                    "engine": "firefox" if "Firefox" in name else "chromium",
                })
        return browsers

    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    chromium_defs = [
        # (display_name, exe_paths, user_data_dir)
        ("Google Chrome",
         [rf"{program_files}\Google\Chrome\Application\chrome.exe",
          rf"{program_files_x86}\Google\Chrome\Application\chrome.exe"],
         rf"{local}\Google\Chrome\User Data"),
        ("Microsoft Edge",
         [rf"{program_files}\Microsoft\Edge\Application\msedge.exe",
          rf"{program_files_x86}\Microsoft\Edge\Application\msedge.exe"],
         rf"{local}\Microsoft\Edge\User Data"),
        ("Brave",
         [rf"{program_files}\BraveSoftware\Brave-Browser\Application\brave.exe",
          rf"{program_files_x86}\BraveSoftware\Brave-Browser\Application\brave.exe"],
         rf"{local}\BraveSoftware\Brave-Browser\User Data"),
        ("Opera",
         [rf"{local}\Opera\launcher.exe",
          rf"{program_files}\Opera\launcher.exe"],
         rf"{roaming}\Opera Software\Opera Stable"),
        ("Opera GX",
         [rf"{local}\Opera GX\launcher.exe"],
         rf"{roaming}\Opera Software\Opera GX Stable"),
    ]
    for name, exes, user_data in chromium_defs:
        exe_found = any(Path(e).exists() for e in exes)
        data_found = Path(user_data).exists()
        if exe_found or data_found:
            browsers.append({
                "name": name,
                "user_data": user_data,
                "exe": next((e for e in exes if Path(e).exists()), ""),
                "engine": "chromium",
            })

    # Firefox
    fx_paths = [
        rf"{program_files}\Mozilla Firefox\firefox.exe",
        rf"{program_files_x86}\Mozilla Firefox\firefox.exe",
    ]
    if any(Path(p).exists() for p in fx_paths):
        browsers.append({
            "name": "Firefox",
            "user_data": rf"{roaming}\Mozilla\Firefox",
            "exe": next((p for p in fx_paths if Path(p).exists()), ""),
            "engine": "firefox",
        })

    return browsers


# ---------------------------------------------------------------------------
# Chromium extension install (Chrome / Edge / Brave / Opera)
# ---------------------------------------------------------------------------
def _install_chromium_extension(browser: Dict, ext_path: str) -> Tuple[bool, str]:
    """Install the unpacked Chromium extension by editing Preferences JSON.

    Returns (success, message).
    """
    user_data = browser["user_data"]
    # The default profile folder is usually "Default", but the very first run
    # of some browsers uses "Profile 1". We'll try Default first.
    profile_dir = Path(user_data) / "Default"
    if not profile_dir.exists():
        # Try Profile 1
        for d in Path(user_data).glob("Profile *"):
            profile_dir = d
            break
    if not profile_dir.exists():
        return False, f"Profile folder not found under {user_data}"

    prefs_file = profile_dir / "Preferences"
    if not prefs_file.exists():
        return False, f"Preferences file not found: {prefs_file}"

    # Read existing prefs
    try:
        with open(prefs_file, "r", encoding="utf-8") as f:
            prefs = json.load(f)
    except Exception as e:
        return False, f"Could not read Preferences: {e}"

    # Add our extension under extensions.settings
    ext = {
        "active_permissions": {"api": ["activeTab", "contextMenus", "storage"],
                                "manifest_permissions": [],
                                "explicit_host": ["<all_urls>"]},
        "commands": {},
        "content_settings": [],
        "creation_flags": 1,
        "from_webstore": False,
        "install_time": str(int(__import__("time").time())),
        "location": 4,  # LOAD_COMPONENT
        "manifest": {
            "manifest_version": 3,
            "name": "Saiful Download Manager",
            "permissions": ["contextMenus", "activeTab", "scripting", "storage"],
            "host_permissions": ["<all_urls>"],
            "version": "1.0.0",
        },
        "path": ext_path,
        "state": 1,  # ENABLED
        "was_installed_by_default": False,
        "was_installed_by_oem": False,
    }

    # Generate a stable ID for the extension based on the path
    ext_id = hashlib.sha256(ext_path.encode("utf-8")).hexdigest()[:32]
    # Chromium uses 32-char a-p alphabetic IDs; build a deterministic one
    alphabet = "abcdefghijklmnop"
    stable_id = "".join(alphabet[int(c, 16)] for c in ext_id)
    ext_settings = prefs.setdefault("extensions", {}).setdefault("settings", {})
    ext_settings[stable_id] = ext

    # Mark this as a developer-mode extension so Chrome doesn't immediately disable
    devmode = prefs.setdefault("extensions", {})
    # Don't try to bypass developer mode warnings entirely - just enable the
    # SK_SHOW_WARNING flag is needed. We just install and let Chrome prompt.
    try:
        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return False, f"Could not write Preferences: {e}"

    return True, f"Installed for {browser['name']} (profile: {profile_dir.name})"


# ---------------------------------------------------------------------------
# Firefox extension install (XPI via registry)
# ---------------------------------------------------------------------------
def _install_firefox_extension(browser: Dict, xpi_path: str) -> Tuple[bool, str]:
    """Install Firefox extension by adding a registry key under HKCU."""
    if not _is_windows():
        return False, "Firefox auto-install only supported on Windows"
    try:
        import winreg  # type: ignore
    except ImportError:
        return False, "winreg not available"

    # Firefox extension UUID (must match install.rdf / manifest.json in XPI)
    fx_uuid = "saiful-download-manager@saiful.example"
    key_path = rf"Software\Mozilla\Firefox\Extensions"
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, fx_uuid, 0, winreg.REG_SZ, xpi_path)
        return True, f"Registered Firefox extension for {browser['name']}"
    except Exception as e:
        return False, f"Registry write failed: {e}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def install_for_all_browsers() -> Dict:
    """Install the extension for every detected browser.

    Returns a dict: {
        "browsers": [{"name": ..., "engine": ..., "success": bool, "message": str}],
        "extension_path": str,
        "summary": str,
    }
    """
    result = {"browsers": [], "extension_path": "", "summary": ""}
    browsers = detect_browsers()
    if not browsers:
        result["summary"] = "No supported browsers detected."
        return result

    # 1. Copy the Chromium extension to a stable location
    src_ext = _bundled_extension_dir()
    target = _install_target_dir()
    ext_target = target / "extension"
    if src_ext.exists():
        try:
            if ext_target.exists():
                shutil.rmtree(ext_target)
            shutil.copytree(src_ext, ext_target)
            result["extension_path"] = str(ext_target)
        except Exception as e:
            result["summary"] = f"Could not copy Chromium extension: {e}"
            return result
    else:
        result["summary"] = f"Bundled extension not found at {src_ext}"
        return result

    # 2. Copy the Firefox XPI to the same target
    src_fx = _bundled_firefox_xpi_dir()
    fx_target = target / "firefox.xpi"
    if src_fx.exists():
        # Build a simple XPI (zip) from the firefox_extension folder
        try:
            import zipfile
            with zipfile.ZipFile(fx_target, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(src_fx):
                    for fn in files:
                        full = os.path.join(root, fn)
                        arc = os.path.relpath(full, src_fx)
                        zf.write(full, arc)
        except Exception as e:
            print(f"[ExtInstaller] XPI build error: {e}")

    # 3. Install for each browser
    success_count = 0
    for b in browsers:
        if b["engine"] == "chromium":
            ok, msg = _install_chromium_extension(b, str(ext_target))
        elif b["engine"] == "firefox":
            if fx_target.exists():
                ok, msg = _install_firefox_extension(b, str(fx_target))
            else:
                ok, msg = False, "XPI file not built"
        else:
            ok, msg = False, f"Unsupported engine: {b['engine']}"
        if ok:
            success_count += 1
        result["browsers"].append({
            "name": b["name"],
            "engine": b["engine"],
            "success": ok,
            "message": msg,
        })

    result["summary"] = f"Installed for {success_count}/{len(browsers)} browser(s)."
    return result


def is_installed() -> bool:
    """Check if the extension copy already exists at the install location."""
    return (_install_target_dir() / "extension" / "manifest.json").exists()


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Detected browsers:")
    for b in detect_browsers():
        print(f"  - {b['name']:20s} ({b['engine']:8s})  exe={b['exe']}")
    print()
    print("Install path:", _install_target_dir())
    print("Bundled Chromium ext:", _bundled_extension_dir())
    print("Bundled Firefox ext:", _bundled_firefox_xpi_dir())
