"""
youtube_grabber.py - YouTube / video grabber using yt-dlp.

Extracts available formats for a URL and downloads the chosen one. yt-dlp
supports YouTube, Vimeo, Facebook, Twitter/X, TikTok and 1000+ other sites.
"""
import os
import threading
import subprocess
from typing import Callable, Optional, List
from dataclasses import dataclass


@dataclass
class VideoFormat:
    format_id: str
    ext: str
    resolution: str
    fps: str
    filesize: float = 0.0
    note: str = ""
    vcodec: str = ""
    acodec: str = ""

    def label(self) -> str:
        size_mb = self.filesize / (1024 * 1024) if self.filesize else 0
        size_str = f"  [{size_mb:.1f} MB]" if size_mb else ""
        return f"{self.resolution} ({self.ext}){size_str} {self.note}".strip()


class YouTubeGrabber:
    """Wraps yt-dlp (Python API) to list formats and download videos."""

    def __init__(self, download_folder: str, config_dict: dict):
        self.download_folder = download_folder
        self.cfg = config_dict
        self._progress = 0.0
        self._speed = 0.0
        self._status = "Idle"
        self._eta = 0.0
        self._filename = ""

    # ------------------------------------------------------------------
    def list_formats(self, url: str, callback: Optional[Callable] = None) -> List[VideoFormat]:
        """Fetch available formats for the URL. Calls callback(error, formats)."""
        try:
            from yt_dlp import YoutubeDL
            ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True,
                        "noplaylist": True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            formats = []
            title = info.get("title", "video")
            self._filename = title
            for f in info.get("formats", []):
                vcodec = f.get("vcodec", "none")
                acodec = f.get("acodec", "none")
                # skip audio-only when there is video counterpart
                resolution = f.get("resolution") or ""
                if not resolution:
                    w = f.get("width") or 0
                    h = f.get("height") or 0
                    if w and h:
                        resolution = f"{w}x{h}"
                    elif h:
                        resolution = f"{h}p"
                fmt = VideoFormat(
                    format_id=str(f.get("format_id", "")),
                    ext=f.get("ext", "mp4"),
                    resolution=resolution or "audio",
                    fps=str(f.get("fps") or ""),
                    filesize=float(f.get("filesize") or f.get("filesize_approx") or 0),
                    note=f.get("format_note", ""),
                    vcodec=vcodec,
                    acodec=acodec,
                )
                formats.append(fmt)
            if callback:
                callback(None, formats, title)
            return formats
        except Exception as e:
            if callback:
                callback(str(e), [], "")
            return []

    # ------------------------------------------------------------------
    def download(self, url: str, format_id: str, ext: str = "mp4",
                 on_progress: Optional[Callable] = None,
                 on_done: Optional[Callable] = None):
        """Download the selected format in a background thread."""
        self._status = "Starting"

        def _hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    self._progress = (downloaded / total) * 100
                self._speed = (d.get("speed") or 0) / 1024  # KB/s
                self._eta = d.get("eta") or 0
                self._status = "Downloading"
                if on_progress:
                    on_progress(self._progress, self._speed, self._eta, self._status)
            elif d["status"] == "finished":
                self._progress = 100.0
                self._status = "Processing..."
                if on_progress:
                    on_progress(self._progress, 0, 0, self._status)
            elif d["status"] == "error":
                self._status = "Error"
                if on_progress:
                    on_progress(self._progress, 0, 0, self._status)

        def _run():
            try:
                from yt_dlp import YoutubeDL
                outtmpl = os.path.join(self.download_folder, "%(title).200s.%(ext)s")
                ydl_opts = {
                    "format": format_id,
                    "outtmpl": outtmpl,
                    "progress_hooks": [_hook],
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                    "merge_output_format": ext if ext in ("mp4", "mkv", "webm") else None,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                self._status = "Complete"
                if on_done:
                    on_done(None, self._filename)
            except Exception as e:
                self._status = f"Error: {e}"
                if on_done:
                    on_done(str(e), self._filename)

        threading.Thread(target=_run, daemon=True, name="ytdl-download").start()

    # ------------------------------------------------------------------
    @staticmethod
    def is_supported_url(url: str) -> bool:
        """Quick check whether the URL looks like a video page."""
        from urllib.parse import urlparse
        host = (urlparse(url).netloc or "").lower()
        keywords = ["youtube", "youtu.be", "vimeo", "facebook", "tiktok",
                    "twitter", "x.com", "dailymotion", "instagram"]
        return any(k in host for k in keywords)
