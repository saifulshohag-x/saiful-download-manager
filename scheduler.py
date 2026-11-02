"""
scheduler.py - Time-based download scheduler.

Starts and stops all downloads within a daily time window. Runs in a background
thread, polling every 15 seconds. When scheduler_enabled is True:
  - At scheduler_start time, call start_all()
  - At scheduler_stop time, call pause_all()
"""
import threading
import time
from datetime import datetime


class Scheduler:
    """Simple daily scheduler for the download queue."""

    def __init__(self, queue_manager):
        self.qm = queue_manager
        self._thread = None
        self._stop_event = threading.Event()
        self._last_state = None  # True = inside active window

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="scheduler")
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                cfg = self.qm.cfg
                if not cfg.get("scheduler_enabled", False):
                    self._last_state = None
                    time.sleep(15)
                    continue
                start_str = cfg.get("scheduler_start", "00:00")
                stop_str = cfg.get("scheduler_stop", "23:59")
                now = datetime.now()
                now_min = now.hour * 60 + now.minute
                start_min = self._parse_hhmm(start_str)
                stop_min = self._parse_hhmm(stop_str)
                if start_min <= stop_min:
                    inside = start_min <= now_min < stop_min
                else:
                    # overnight window
                    inside = now_min >= start_min or now_min < stop_min
                if inside and self._last_state is not True:
                    # entering active window
                    self.qm.start_all()
                    self._last_state = True
                elif not inside and self._last_state is not False:
                    self.qm.pause_all()
                    self._last_state = False
            except Exception as e:
                print(f"[Scheduler] error: {e}")
            time.sleep(15)

    @staticmethod
    def _parse_hhmm(s: str) -> int:
        h, m = s.split(":")
        return int(h) * 60 + int(m)
