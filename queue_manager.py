"""
queue_manager.py - Download queue + categories + history integration.
"""
import os
import threading
from typing import Callable, Optional, List
from download_engine import (
    DownloadTask, DownloadEngine,
    STATUS_QUEUED, STATUS_DOWNLOADING, STATUS_COMPLETE, STATUS_ERROR,
    STATUS_PAUSED, STATUS_STOPPED,
)
from categories import get_category_id, get_target_folder
from history import History


class QueueManager:
    def __init__(self, config_dict: dict, history: History = None):
        self.cfg = config_dict
        self.tasks: List[DownloadTask] = []
        self.engines = {}
        self._lock = threading.RLock()
        self.on_list_changed: Optional[Callable] = None
        self.on_progress: Optional[Callable] = None
        self.on_status: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None  # called when a task completes
        self.history = history or History(config_dict.get("history_keep_days", 30))

    def _schedule_next(self):
        with self._lock:
            running = sum(1 for t in self.tasks if t.status == STATUS_DOWNLOADING)
            if running >= self.cfg.get("max_concurrent", 5):
                return
            for t in self.tasks:
                if t.status == STATUS_QUEUED:
                    self._start_internal(t)
                    return

    def _start_internal(self, task: DownloadTask) -> bool:
        if id(task) in self.engines:
            eng = self.engines[id(task)]
            return eng.resume() if task.status == STATUS_PAUSED else eng.start()
        eng = DownloadEngine(task, self.cfg)
        task.on_progress = self._on_progress
        task.on_status = self._on_status
        self.engines[id(task)] = eng
        return eng.start()

    def add(self, url: str, file_name: str = "", auto_start: bool = True,
            category: str = "") -> DownloadTask:
        from download_engine import create_task
        # Determine target folder based on category or auto-detect
        base = self.cfg.get("download_folder", "")
        if not file_name:
            from urllib.parse import urlparse, unquote
            path = urlparse(url).path
            file_name = unquote(os.path.basename(path)) or "download.bin"
        if self.cfg.get("categories_enabled", True) and self.cfg.get("category_folders", True):
            target = get_target_folder(base, file_name, use_subfolders=True)
        else:
            target = base
        task = create_task(url, file_name, target)
        task.status = STATUS_QUEUED
        with self._lock:
            self.tasks.append(task)
        if self.on_list_changed:
            self.on_list_changed()
        if auto_start and self.cfg.get("auto_start", True):
            self._schedule_next()
        return task

    def start(self, task: DownloadTask):
        with self._lock:
            self._start_internal(task)
        self._schedule_next()

    def start_all(self):
        with self._lock:
            for t in list(self.tasks):
                if t.status in (STATUS_QUEUED, STATUS_PAUSED, STATUS_ERROR):
                    self._start_internal(t)
        self._schedule_next()

    def pause(self, task: DownloadTask):
        eng = self.engines.get(id(task))
        if eng:
            eng.pause()
        self._schedule_next()

    def pause_all(self):
        for t in list(self.tasks):
            if t.status == STATUS_DOWNLOADING:
                self.pause(t)

    def resume(self, task: DownloadTask):
        self.start(task)

    def stop(self, task: DownloadTask):
        eng = self.engines.get(id(task))
        if eng:
            eng.stop()
        self._schedule_next()

    def stop_all(self):
        for t in list(self.tasks):
            if t.status == STATUS_DOWNLOADING:
                self.stop(t)

    def remove(self, task: DownloadTask, delete_files: bool = False):
        with self._lock:
            eng = self.engines.get(id(task))
            if eng:
                eng.stop()
                self.engines.pop(id(task), None)
            if task in self.tasks:
                self.tasks.remove(task)
        if delete_files:
            try:
                if task.file_path and os.path.exists(task.file_path):
                    os.remove(task.file_path)
                meta = task.file_path + ".meta" if task.file_path else None
                if meta and os.path.exists(meta):
                    os.remove(meta)
            except Exception:
                pass
        if self.on_list_changed:
            self.on_list_changed()
        self._schedule_next()

    def clear_completed(self):
        with self._lock:
            self.tasks = [t for t in self.tasks if t.status != STATUS_COMPLETE]
        if self.on_list_changed:
            self.on_list_changed()

    def get_all(self) -> List[DownloadTask]:
        return list(self.tasks)

    def get_by_category(self, category_id: str) -> List[DownloadTask]:
        """Return tasks matching a category id."""
        if category_id == "all":
            return list(self.tasks)
        if category_id == "unfinished":
            return [t for t in self.tasks if t.status not in (STATUS_COMPLETE,)]
        if category_id == "finished":
            return [t for t in self.tasks if t.status == STATUS_COMPLETE]
        # File-type category
        from categories import get_category_id
        return [t for t in self.tasks
                if get_category_id(t.file_name or "") == category_id]

    def update_config(self, new_cfg: dict):
        self.cfg.update(new_cfg)
        for eng in self.engines.values():
            eng.set_speed_limit(self.cfg.get("speed_limit_kbps", 0))

    def _on_progress(self, task: DownloadTask):
        if self.on_progress:
            try:
                self.on_progress(task)
            except Exception:
                pass

    def _on_status(self, task: DownloadTask):
        if task.status in (STATUS_COMPLETE, STATUS_ERROR, STATUS_STOPPED):
            self.engines.pop(id(task), None)
            self._schedule_next()
            # Record in history
            try:
                self.history.add(task.url, task.file_name, task.file_path,
                                 task.file_size, task.status, task.error)
            except Exception:
                pass
            # Fire completion callback (for sound, antivirus, auto-shutdown)
            if task.status == STATUS_COMPLETE and self.on_complete:
                try:
                    self.on_complete(task)
                except Exception:
                    pass
        if self.on_status:
            try:
                self.on_status(task)
            except Exception:
                pass

    def total_speed_kbps(self) -> float:
        return sum(t.speed_kbps for t in self.tasks if t.status == STATUS_DOWNLOADING)

    def active_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == STATUS_DOWNLOADING)

    def queue_count(self) -> int:
        return sum(1 for t in self.tasks if t.status == STATUS_QUEUED)
