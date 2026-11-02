# Saiful Download Manager - Browser Extension (Chromium)

A Chrome/Edge/Brave/Opera (manifest v3) extension that sends download links
to the **Saiful Download Manager** desktop app.

## Auto-install

When you install Saiful Download Manager on Windows and run it for the first
time, the app **automatically** copies this extension to:

    %LOCALAPPDATA%\SaifulDownloadManager\extension

and registers it with every Chromium-based browser it finds (Chrome, Edge,
Brave, Opera, Opera GX). On the next browser launch, the browser will load
the extension automatically. You may see a one-time "Disable developer mode
extensions" prompt — just click **Keep**.

## Manual install (if auto-install didn't trigger)

1. Open `chrome://extensions` (or `edge://extensions`, `brave://extensions`, etc.).
2. Turn on **Developer mode** (top-right toggle).
3. Click **Load unpacked**.
4. Select this `saiful_ext` folder.
5. Make sure the Saiful Download Manager desktop app is running (port 9527).

## How to use

- Right-click any link → **Download with Saiful Download Manager**.
- Right-click any video/audio → same option.
- Click the toolbar icon → send current page URL.
- Right-click the toolbar icon → **Options** to change the port.
