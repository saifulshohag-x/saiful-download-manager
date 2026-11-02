# Saiful Download Manager v2.0

A complete **Internet Download Manager (IDM) clone** for Windows 10/11 64-bit,
built with Python + CustomTkinter. Now with **video overlay button on every
video**, full IDM-style UI, categories, scheduler, grabber, and more.

## What's new in v2.0 (IDM-style rewrite)

| Feature | Description |
|---------|-------------|
| **🎬 Video overlay button** | A green "⬇ SDM" button appears on top of every `<video>`, `<audio>`, `<embed>`, `<object>` element on every web page — exactly like IDM. |
| **🔗 Download link overlay** | A small "⬇" button appears next to every direct download link (.zip, .pdf, .mp4, .exe, etc.) on web pages. |
| **📂 IDM-style categories** | Left sidebar with All Downloads / Unfinished / Finished / Grabber / Drop Box, plus file-type categories: Compressed, Documents, Music, Programs, Video, Images. Files auto-sort into category subfolders. |
| **📊 Speed graph** | Real-time scrolling speed graph at the bottom of the main window (just like IDM). |
| **🧰 System tray** | Minimize to tray; quick actions from tray menu (Open / Add URL / Pause All / Resume All / Quit). |
| **📋 Clipboard monitor** | When you copy a download URL, SDM asks if you want to add it. |
| **🔔 Sound notifications** | Plays Windows sounds on download complete / added / error. |
| **📚 Download history** | All completed/failed downloads are logged in `~/.saiful_dm/history.json`. |
| **🕸️ Site Grabber** | Extract every downloadable file from any web page. |
| **🔢 Batch download** | URL patterns like `https://example.com/file[01-10].zip` expand to 10 URLs. |
| **🛡️ Antivirus scan** | Optional Windows Defender scan on download complete. |
| **📅 Scheduler with days** | Pick which days of the week + start/stop times + auto-shutdown. |
| **⏱️ Auto-shutdown** | Optional: shut down PC when all downloads finish. |

## Existing v1.0 features (kept)

- 16-segment parallel downloads (high speed)
- TCP_NODELAY, 256 KB chunks, 128-connection pool
- Pause/Resume with `.meta` sidecar (survives app restart)
- Auto-install extension for Chrome/Edge/Brave/Opera/Opera GX/Firefox
- Video Grabber (YouTube/Vimeo/TikTok/1000+ sites via yt-dlp)
- Local HTTP server on port 9527
- Dark theme, English UI

## Quick Start

### Run from source
```bat
pip install -r requirements.txt
python main.py
```

### Build standalone .exe (recommended)
1. Install Python 3.10+ from https://python.org (tick "Add to PATH")
2. Double-click `build_exe.bat`
3. Get `dist\SaifulDownloadManager.exe` (~80 MB)
4. Run anywhere — no Python needed

### Auto-build via GitHub Actions
1. Push this folder to a new GitHub repo
2. Go to **Actions** tab → "Build Windows EXE" runs automatically
3. Download `.exe` from workflow artifacts
4. Tag a release: `git tag v2.0.0 && git push --tags`

## Browser Extension

Auto-installs into Chrome, Edge, Brave, Opera, Opera GX, Firefox on first launch.

**Two overlay features on every web page:**

1. **Video overlay** — A green "⬇ SDM" button appears in the top-left corner of every video. Click it to send the video URL to Saiful Download Manager.

2. **Download link overlay** — A small green "⬇" button appears right after every direct download link (any link ending in `.zip`, `.pdf`, `.mp4`, `.exe`, etc.).

Both also work via the right-click context menu:
- Right-click any link → **Download with Saiful Download Manager**
- Right-click any video/audio → same option
- Click the toolbar icon → send current page URL

## UI Layout (matches IDM)

```
+-----------------------------------------------------+
| Tasks  Downloads  View  Help                        |
+-----------------------------------------------------+
| [Add URL] [Resume] [Pause] [Stop] [Clear]           |
| [Grabber] [Video] [Scheduler] [Browser Ext] [Opts]  |
+---------+-------------------------------------------+
|Sidebar  | File Name / Status       Size  Spd  ETA  |
| All DL  +-------------------------------------------+
| Unfin.  | 🎬 video.mp4    Downloading  4.2 MB/s     |
| Fin.    |    [==============>     ] 65%             |
| Comp.   |                                          |
| Doc.    | 📦 archive.zip  Complete                  |
| Music   |    [====================] 100%            |
| Prog.   |                                          |
| Video   |                                          |
| Images  |                                          |
| Grabber |                                          |
| DropBox | +--- Speed Graph --------------------+   |
|         | |     /\    /\                        |   |
|         | |    /  \  /  \  /                    |   |
|         | +-----------------------------------+    |
+---------+-------------------------------------------+
| Speed: 4.2 MB/s | Active: 3 | Queued: 5            |
+-----------------------------------------------------+
```

## File Layout

```
saiful_dm/
├── main.py                    # Entry point
├── gui.py                     # IDM-style main window
├── dialogs.py                 # Add URL / Batch / Settings / Scheduler / Grabber dialogs
├── download_engine.py         # 16-segment parallel download engine
├── queue_manager.py           # Queue + categories + history integration
├── scheduler.py               # Daily time-window scheduler
├── youtube_grabber.py         # yt-dlp wrapper
├── browser_integration.py     # Local HTTP server (port 9527)
├── extension_installer.py     # Auto-install extensions
├── categories.py              # File-type categories (NEW)
├── speed_graph.py             # Real-time speed graph widget (NEW)
├── system_tray.py             # System tray icon (NEW)
├── sound_notification.py      # Sound on completion (NEW)
├── clipboard_monitor.py       # Clipboard URL detector (NEW)
├── history.py                 # Download history (NEW)
├── site_grabber.py            # Web page link extractor (NEW)
├── batch_download.py          # URL pattern expander (NEW)
├── antivirus.py               # Windows Defender scan (NEW)
├── config.py                  # Settings (~/.saiful_dm/config.json)
├── requirements.txt
├── build_exe.bat
├── extension/saiful_ext/      # Chromium extension
│   ├── manifest.json
│   ├── background.js
│   ├── content.js             # Video & link overlay (NEW)
│   ├── content.css            # Overlay button styles (NEW)
│   ├── options.html
│   └── icons/
├── firefox_extension/         # Firefox XPI source
│   ├── manifest.json
│   ├── background.js
│   ├── content.js             # Same overlay (NEW)
│   ├── content.css
│   ├── options.html
│   └── icons/
└── .github/workflows/build-exe.yml  # Auto-build on Windows runner
```

## License

MIT.
