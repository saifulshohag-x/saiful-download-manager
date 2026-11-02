"""
download_engine.py - High-speed multi-segment HTTP download engine.

Improvements for high speed:
- Default 16 segments per file (configurable up to 32)
- 256 KB chunk size (vs 64 KB) — fewer syscalls, better throughput
- TCP_NODELAY on the socket (disables Nagle's algorithm)
- Large connection pool (128 connections per host)
- Aggressive retries with exponential backoff
- No speed limit by default (user can set one)
"""
import os
import json
import time
import socket
import threading
import urllib3
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Callable
from urllib3.util.retry import Retry

import requests
from requests.adapters import HTTPAdapter

# Disable insecure request warnings (we accept any SSL server)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_session(cfg: dict) -> requests.Session:
    """Build a requests.Session tuned for high-speed multi-segment downloads."""
    s = requests.Session()
    retry = Retry(
        total=cfg.get("retries", 10),
        connect=10,
        read=10,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 503, 504, 408, 429),
        allowed_methods=("GET", "HEAD"),
    )
    pool = cfg.get("pool_connections", 128)
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=pool,
        pool_maxsize=cfg.get("pool_maxsize", 128),
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent": cfg.get("user_agent", ""),
        "Accept-Encoding": "identity",  # raw bytes - required for Range
        "Accept": "*/*",
        "Connection": "keep-alive",
    })
    return s


def human_size(num: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num) < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} PB"


def human_speed(kbps: float) -> str:
    if kbps < 1024:
        return f"{kbps:.1f} KB/s"
    return f"{kbps/1024:.2f} MB/s"


def eta_str(seconds: float) -> str:
    if seconds <= 0 or seconds > 3600 * 999:
        return "--:--:--"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------
@dataclass
class Segment:
    index: int
    start: int
    end: int
    current: int
    done: bool = False

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------
STATUS_QUEUED = "Queued"
STATUS_CONNECTING = "Connecting"
STATUS_DOWNLOADING = "Downloading"
STATUS_PAUSED = "Paused"
STATUS_COMPLETE = "Complete"
STATUS_ERROR = "Error"
STATUS_MERGING = "Merging"
STATUS_STOPPED = "Stopped"


# ---------------------------------------------------------------------------
# DownloadTask
# ---------------------------------------------------------------------------
@dataclass
class DownloadTask:
    url: str
    file_path: str
    file_name: str
    file_size: int = 0
    downloaded: int = 0
    status: str = STATUS_QUEUED
    segments: list = field(default_factory=list)
    speed_kbps: float = 0.0
    eta_seconds: float = 0.0
    error: str = ""
    supports_resume: bool = False
    _session: Optional[requests.Session] = field(default=None, repr=False)
    _threads: list = field(default_factory=list, repr=False)
    _stop_event: Optional[threading.Event] = field(default=None, repr=False)
    _pause_event: Optional[threading.Event] = field(default=None, repr=False)
    _progress_lock: Optional[threading.Lock] = field(default=None, repr=False)
    _meta_path: Optional[str] = field(default=None, repr=False)
    _start_time: float = 0.0
    _last_sample_time: float = 0.0
    _last_sample_bytes: int = 0
    on_progress: Optional[Callable] = field(default=None, repr=False)
    on_status: Optional[Callable] = field(default=None, repr=False)

    @property
    def progress_pct(self) -> float:
        if self.file_size <= 0:
            return 0.0
        return min(100.0, (self.downloaded / self.file_size) * 100.0)

    # --- meta file persistence ------------------------------------------------
    def save_meta(self):
        if not self.file_path:
            return
        self._meta_path = self.file_path + ".meta"
        data = {
            "url": self.url,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "downloaded": self.downloaded,
            "segments": [s.to_dict() for s in self.segments],
            "supports_resume": self.supports_resume,
        }
        try:
            with open(self._meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Meta] save error: {e}")

    def load_meta(self) -> bool:
        if not self.file_path:
            return False
        self._meta_path = self.file_path + ".meta"
        if not Path(self._meta_path).exists():
            return False
        try:
            with open(self._meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("url") != self.url:
                return False
            self.file_size = data.get("file_size", 0)
            self.downloaded = data.get("downloaded", 0)
            self.supports_resume = data.get("supports_resume", False)
            self.segments = [Segment.from_dict(s) for s in data.get("segments", [])]
            return True
        except Exception as e:
            print(f"[Meta] load error: {e}")
            return False

    def delete_meta(self):
        try:
            if self._meta_path and Path(self._meta_path).exists():
                Path(self._meta_path).unlink()
        except Exception:
            pass

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "downloaded": self.downloaded,
            "status": self.status,
            "speed_kbps": self.speed_kbps,
            "eta_seconds": self.eta_seconds,
            "progress_pct": self.progress_pct,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# DownloadEngine
# ---------------------------------------------------------------------------
class DownloadEngine:
    """Manages a single DownloadTask. Spawns one thread per segment."""

    def __init__(self, task: DownloadTask, config_dict: dict):
        self.task = task
        self.cfg = config_dict
        self._session = _make_session(config_dict)
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused
        self._lock = threading.Lock()
        self._speed_limit_kbps = config_dict.get("speed_limit_kbps", 0)
        self._chunk_size = config_dict.get("chunk_size", 262144)
        self._tcp_nodelay = config_dict.get("tcp_nodelay", True)
        task._session = self._session
        task._stop_event = self._stop_event
        task._pause_event = self._pause_event
        task._progress_lock = self._lock
        self._budget = 0.0
        self._budget_t = time.monotonic()

    # ----------------------------------------------------------------------
    def set_speed_limit(self, kbps: int):
        self._speed_limit_kbps = max(0, kbps)

    # ----------------------------------------------------------------------
    def _set_status(self, status: str, error: str = ""):
        self.task.status = status
        if error:
            self.task.error = error
        if self.task.on_status:
            try:
                self.task.on_status(self.task)
            except Exception:
                pass

    # ----------------------------------------------------------------------
    def _probe(self) -> bool:
        """HEAD/GET to learn file size and resume support."""
        task = self.task
        self._set_status(STATUS_CONNECTING)
        try:
            r = self._session.head(task.url, allow_redirects=True,
                                   timeout=self.cfg.get("timeout", 60), stream=True)
            if r.status_code >= 400 or r.status_code == 405:
                r = self._session.get(task.url, stream=True,
                                      timeout=self.cfg.get("timeout", 60),
                                      headers={"Range": "bytes=0-0"})
            file_size = 0
            supports_resume = False
            if "Content-Range" in r.headers:
                cr = r.headers["Content-Range"]
                try:
                    file_size = int(cr.split("/")[-1])
                    supports_resume = True
                except Exception:
                    pass
            if file_size == 0 and "Content-Length" in r.headers:
                try:
                    file_size = int(r.headers["Content-Length"])
                except Exception:
                    pass
            if "Accept-Ranges" in r.headers and r.headers["Accept-Ranges"].lower() == "bytes":
                supports_resume = True
            if not task.file_name:
                cd = r.headers.get("Content-Disposition", "")
                if "filename=" in cd:
                    name = cd.split("filename=")[-1].strip('"\' ')
                    task.file_name = name
                else:
                    from urllib.parse import urlparse, unquote
                    path = urlparse(task.url).path
                    task.file_name = unquote(os.path.basename(path)) or "download.bin"
            task.file_size = max(0, file_size)
            # Verify range support with actual ranged GET
            if supports_resume and file_size > 1:
                try:
                    test = self._session.get(task.url, stream=True,
                                             timeout=self.cfg.get("timeout", 60),
                                             headers={"Range": "bytes=0-0"})
                    if test.status_code != 206:
                        supports_resume = False
                    test.close()
                except Exception:
                    supports_resume = False
            task.supports_resume = supports_resume and file_size > 0
            task.file_path = os.path.join(self.cfg["download_folder"], task.file_name)
            return True
        except Exception as e:
            self._set_status(STATUS_ERROR, str(e))
            return False

    # ----------------------------------------------------------------------
    def _build_segments(self):
        task = self.task
        n = self.cfg.get("segments", 16) if task.supports_resume else 1
        n = max(1, min(32, n))
        if not task.segments:
            size = task.file_size
            if size == 0 or n == 1:
                task.segments = [Segment(0, 0, max(0, size - 1), 0)]
                return
            chunk = size // n
            task.segments = []
            for i in range(n):
                start = i * chunk
                end = (size - 1) if i == n - 1 else (start + chunk - 1)
                task.segments.append(Segment(i, start, end, start))
        for s in task.segments:
            if s.end > 0 and s.current >= s.end:
                s.done = True

    # ----------------------------------------------------------------------
    def _worker(self, seg: Segment):
        """Download one segment using HTTP Range."""
        task = self.task
        try:
            f = open(task.file_path, "r+b")
        except FileNotFoundError:
            f = open(task.file_path, "wb")
        consecutive_failures = 0
        try:
            while not seg.done and not self._stop_event.is_set():
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break
                if task.supports_resume:
                    headers = {"Range": f"bytes={seg.current}-{seg.end}"}
                else:
                    headers = {}
                try:
                    r = self._session.get(task.url, headers=headers, stream=True,
                                          timeout=self.cfg.get("timeout", 60))
                    if r.status_code not in (200, 206):
                        raise RuntimeError(f"HTTP {r.status_code}")
                    # Set TCP_NODELAY on the underlying socket for low latency
                    if self._tcp_nodelay:
                        try:
                            raw = getattr(r.raw, "_fp", None)
                            sock = getattr(raw, "fp", None)
                            if sock and hasattr(sock, "fileno"):
                                s = socket.fromfd(sock.fileno(), socket.AF_INET,
                                                  socket.SOCK_STREAM)
                                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                                s.detach()
                        except Exception:
                            pass
                    consecutive_failures = 0
                    pos = seg.current
                    for chunk in r.iter_content(chunk_size=self._chunk_size):
                        if self._stop_event.is_set():
                            break
                        if not self._pause_event.is_set():
                            self._pause_event.wait()
                        if not chunk:
                            continue
                        f.seek(pos)
                        f.write(chunk)
                        pos += len(chunk)
                        with self._lock:
                            seg.current = pos
                            task.downloaded += len(chunk)
                            self._throttle(len(chunk))
                            self._sample_speed()
                        if task.on_progress:
                            try:
                                task.on_progress(task)
                            except Exception:
                                pass
                    r.close()
                    if pos >= seg.end or seg.end == 0 or not task.supports_resume:
                        seg.done = True
                except Exception as e:
                    print(f"[Worker {seg.index}] error: {e}")
                    consecutive_failures += 1
                    if self._stop_event.is_set():
                        break
                    if consecutive_failures >= self.cfg.get("retries", 10):
                        with self._lock:
                            task.error = str(e)
                        self._stop_event.set()
                        break
                    time.sleep(0.5)
        finally:
            f.close()

    # ----------------------------------------------------------------------
    def _throttle(self, bytes_written: int):
        if self._speed_limit_kbps <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._budget_t
        self._budget += elapsed * self._speed_limit_kbps * 1024
        self._budget_t = now
        self._budget -= bytes_written
        if self._budget < 0:
            sleep_for = (-self._budget) / (self._speed_limit_kbps * 1024)
            if sleep_for > 0:
                time.sleep(min(sleep_for, 0.5))

    # ----------------------------------------------------------------------
    def _sample_speed(self):
        task = self.task
        now = time.time()
        if task._last_sample_time == 0:
            task._last_sample_time = now
            task._last_sample_bytes = task.downloaded
            return
        dt = now - task._last_sample_time
        if dt < 0.4:
            return
        db = task.downloaded - task._last_sample_bytes
        if db < 0:
            db = 0
        kbps = (db / 1024.0) / dt
        task.speed_kbps = 0.6 * task.speed_kbps + 0.4 * kbps if task.speed_kbps else kbps
        task._last_sample_time = now
        task._last_sample_bytes = task.downloaded
        if task.speed_kbps > 0 and task.file_size > task.downloaded:
            remaining_kb = (task.file_size - task.downloaded) / 1024.0
            task.eta_seconds = remaining_kb / task.speed_kbps
        else:
            task.eta_seconds = 0

    # ----------------------------------------------------------------------
    def _preallocate(self):
        task = self.task
        if not task.supports_resume or task.file_size <= 0:
            return
        if not os.path.exists(task.file_path):
            with open(task.file_path, "wb") as f:
                f.truncate(task.file_size)
        else:
            cur = os.path.getsize(task.file_path)
            if cur < task.file_size:
                with open(task.file_path, "r+b") as f:
                    f.truncate(task.file_size)

    # ----------------------------------------------------------------------
    def start(self):
        task = self.task
        if task.status in (STATUS_DOWNLOADING, STATUS_CONNECTING, STATUS_MERGING):
            return True
        if not task.file_size or not task.file_path:
            if not self._probe():
                return False
        if task.status == STATUS_QUEUED and not task.segments:
            task.load_meta()
        self._build_segments()
        self._preallocate()
        self._stop_event = threading.Event()
        self._pause_event.set()
        self._set_status(STATUS_DOWNLOADING)
        task._start_time = time.time()
        task._threads = [t for t in task._threads if t.is_alive()]
        for seg in task.segments:
            if seg.done:
                continue
            already_running = any(getattr(t, "_seg_index", None) == seg.index
                                  and t.is_alive() for t in task._threads)
            if already_running:
                continue
            t = threading.Thread(target=self._worker, args=(seg,), daemon=True,
                                 name=f"dl-{task.file_name}-{seg.index}")
            t._seg_index = seg.index  # type: ignore
            t.start()
            task._threads.append(t)
        if not task._threads:
            self._watch_inline()
            return True
        watcher = threading.Thread(target=self._watch, daemon=True)
        watcher.start()
        return True

    def _watch_inline(self):
        task = self.task
        if all(s.done for s in task.segments):
            self._set_status(STATUS_COMPLETE)
            task.speed_kbps = 0
            task.eta_seconds = 0
            task.delete_meta()
        else:
            self._set_status(STATUS_PAUSED)
            task.save_meta()

    # ----------------------------------------------------------------------
    def _watch(self):
        task = self.task
        my_threads = list(task._threads)
        for t in my_threads:
            t.join()
        if self._stop_event.is_set():
            if task.error:
                self._set_status(STATUS_ERROR, task.error)
            else:
                self._set_status(STATUS_STOPPED)
            task.save_meta()
            return
        if all(s.done for s in task.segments):
            self._set_status(STATUS_COMPLETE)
            task.speed_kbps = 0
            task.eta_seconds = 0
            task.delete_meta()
        else:
            self._set_status(STATUS_PAUSED)
            task.save_meta()

    # ----------------------------------------------------------------------
    def pause(self):
        self._pause_event.clear()
        self._set_status(STATUS_PAUSED)
        task = self.task
        def _save():
            time.sleep(0.2)
            task.save_meta()
        threading.Thread(target=_save, daemon=True).start()

    def resume(self):
        self._pause_event.set()
        task = self.task
        if task.status != STATUS_PAUSED:
            return
        alive = any(t.is_alive() for t in task._threads)
        if alive:
            self._set_status(STATUS_DOWNLOADING)
        else:
            self.start()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self._set_status(STATUS_STOPPED)

    def is_running(self) -> bool:
        return self.task.status in (STATUS_DOWNLOADING, STATUS_CONNECTING, STATUS_MERGING)


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------
def create_task(url: str, file_name: str = "", download_folder: str = "") -> DownloadTask:
    if not file_name:
        from urllib.parse import urlparse, unquote
        path = urlparse(url).path
        file_name = unquote(os.path.basename(path)) or "download.bin"
    folder = download_folder or os.path.join(str(Path.home()), "Downloads")
    file_path = os.path.join(folder, file_name)
    return DownloadTask(url=url, file_path=file_path, file_name=file_name)
