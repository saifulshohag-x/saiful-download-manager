"""
gui.py - IDM-style main window for Saiful Download Manager.

Layout (matches IDM Classic):
  +------------------------------------+
  | Menu bar: Tasks Downloads View Help|
  +------------------------------------+
  | Toolbar (icon buttons)             |
  +---------+--------------------------+
  |Sidebar  | Download list (columns)  |
  |tree:    |   icon | name | size |   |
  | All DL  |   status | speed | eta   |
  | Unfin.  |                          |
  | Fin.    |                          |
  | Comp.   |   [Speed graph bottom]   |
  | Doc.    |                          |
  | Music   |                          |
  | ...     |                          |
  +---------+--------------------------+
  | Status bar                          |
  +------------------------------------+
"""
import os
import sys
import time
import threading
import subprocess
import customtkinter as ctk
from tkinter import messagebox

from config import config, APP_NAME, APP_VERSION
from queue_manager import QueueManager
from scheduler import Scheduler
from browser_integration import BrowserIntegrationServer
from history import History
from categories import CATEGORIES, VIRTUAL_CATEGORIES, get_category_id, get_category_info, get_file_icon
from speed_graph import SpeedGraph
from system_tray import SystemTray
import sound_notification as sounds
from clipboard_monitor import ClipboardMonitor
from download_engine import (
    human_size, human_speed, eta_str,
    STATUS_QUEUED, STATUS_DOWNLOADING, STATUS_PAUSED,
    STATUS_COMPLETE, STATUS_ERROR, STATUS_STOPPED, STATUS_CONNECTING,
)
from dialogs import (
    AddURLDialog, BatchDownloadDialog, SettingsDialog, SchedulerDialog,
    VideoGrabberDialog, SiteGrabberDialog, BrowserExtensionsDialog,
)


ACCENT = "#0fb84c"
ACCENT_HOVER = "#0a9d3f"
DANGER = "#e0533d"
BG = "#1e1e1e"
ROW_BG = "#2a2a2a"
ROW_BG_ALT = "#252525"
ROW_BG_SEL = "#0d3d1f"


# ---------------------------------------------------------------------------
# Download row (one entry in the main list, looks like IDM)
# ---------------------------------------------------------------------------
class DownloadRow(ctk.CTkFrame):
    def __init__(self, master, task, on_pause, on_resume, on_stop, on_remove, on_open):
        super().__init__(master, fg_color=ROW_BG, corner_radius=4)
        self.task = task
        self._on_pause = on_pause
        self._on_resume = on_resume
        self._on_stop = on_stop
        self._on_remove = on_remove
        self._on_open = on_open

        self.grid_columnconfigure(1, weight=1)

        # Left: file type icon
        self.icon_label = ctk.CTkLabel(self, text=get_file_icon(task.file_name or ""),
                                       width=44, font=ctk.CTkFont(size=22))
        self.icon_label.grid(row=0, column=0, padx=(8, 4), pady=8, sticky="n")

        # Right: content
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=8)
        right.grid_columnconfigure(0, weight=1)

        # Top line: name + status badge
        top = ctk.CTkFrame(right, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        self.name_label = ctk.CTkLabel(top, text=task.file_name or task.url,
                                       anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
        self.name_label.grid(row=0, column=0, sticky="ew")
        self.status_label = ctk.CTkLabel(top, text=task.status, anchor="e",
                                         text_color=ACCENT, width=110,
                                         font=ctk.CTkFont(size=11, weight="bold"))
        self.status_label.grid(row=0, column=1, sticky="e", padx=(8, 0))

        # Progress bar
        self.progress = ctk.CTkProgressBar(right, height=12, progress_color=ACCENT)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(4, 2))
        self.progress.set(0)

        # Stats line
        stats = ctk.CTkFrame(right, fg_color="transparent")
        stats.grid(row=2, column=0, sticky="ew", pady=(2, 0))
        stats.grid_columnconfigure(0, weight=1)
        self.stats_label = ctk.CTkLabel(stats, text="", anchor="w",
                                        text_color="#a0a0a0",
                                        font=ctk.CTkFont(size=11))
        self.stats_label.grid(row=0, column=0, sticky="w")
        # Action buttons (right)
        btn_frame = ctk.CTkFrame(stats, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")
        self.pause_btn = ctk.CTkButton(btn_frame, text="⏸", width=30, height=26,
                                       font=ctk.CTkFont(size=14),
                                       command=self._pause)
        self.pause_btn.pack(side="left", padx=2)
        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹", width=30, height=26,
                                      font=ctk.CTkFont(size=14),
                                      fg_color=DANGER, hover_color="#b3422f",
                                      command=self._stop)
        self.stop_btn.pack(side="left", padx=2)
        self.remove_btn = ctk.CTkButton(btn_frame, text="✕", width=30, height=26,
                                        font=ctk.CTkFont(size=12),
                                        fg_color="#444", hover_color="#555",
                                        command=self._remove)
        self.remove_btn.pack(side="left", padx=2)
        self.open_btn = ctk.CTkButton(btn_frame, text="📂", width=30, height=26,
                                      font=ctk.CTkFont(size=13),
                                      fg_color="#444", hover_color="#555",
                                      command=self._open)
        self.open_btn.pack(side="left", padx=2)

        self.refresh()

    def refresh(self):
        t = self.task
        self.name_label.configure(text=t.file_name or t.url)
        self.icon_label.configure(text=get_file_icon(t.file_name or ""))
        self.status_label.configure(text=t.status)
        if t.file_size > 0:
            self.progress.set(t.downloaded / t.file_size)
        elif t.status == STATUS_COMPLETE:
            self.progress.set(1.0)
        else:
            self.progress.set(0)
        if t.status == STATUS_COMPLETE:
            self.stats_label.configure(text=f"{human_size(t.file_size)}  •  Done", text_color="#a0a0a0")
        elif t.status == STATUS_DOWNLOADING:
            self.stats_label.configure(
                text=f"{human_size(t.downloaded)} / {human_size(t.file_size)}  "
                     f"({t.progress_pct:.1f}%)  •  {human_speed(t.speed_kbps)}  •  ETA {eta_str(t.eta_seconds)}",
                text_color="#a0a0a0")
        elif t.status == STATUS_PAUSED:
            self.stats_label.configure(
                text=f"{human_size(t.downloaded)} / {human_size(t.file_size)}  ({t.progress_pct:.1f}%)  •  Paused",
                text_color="#a0a0a0")
        elif t.status == STATUS_ERROR:
            self.stats_label.configure(text=f"Error: {t.error[:80]}", text_color=DANGER)
        else:
            self.stats_label.configure(text=t.status, text_color="#a0a0a0")
        if t.status == STATUS_DOWNLOADING:
            self.pause_btn.configure(text="⏸", state="normal", command=self._pause)
        elif t.status == STATUS_PAUSED:
            self.pause_btn.configure(text="▶", state="normal", command=self._resume)
        elif t.status in (STATUS_QUEUED, STATUS_STOPPED, STATUS_ERROR):
            self.pause_btn.configure(text="▶", state="normal", command=self._resume)
        elif t.status == STATUS_COMPLETE:
            self.pause_btn.configure(text="✓", state="disabled")
        self.stop_btn.configure(state=("normal" if t.status == STATUS_DOWNLOADING else "disabled"))

    def _pause(self): self._on_pause(self.task)
    def _resume(self): self._on_resume(self.task)
    def _stop(self): self._on_stop(self.task)
    def _remove(self): self._on_remove(self.task)
    def _open(self): self._on_open(self.task)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode(config.get("appearance", "dark"))
        ctk.set_default_color_theme("green")

        self.title(f"{APP_NAME} v{APP_VERSION}")
        w, h = (config.get("window_size", "1280x720") or "1280x720").split("x")
        self.geometry(f"{int(w)}x{int(h)}")
        self.minsize(1000, 600)

        # Backend
        self.history = History(config.get("history_keep_days", 30))
        self.qm = QueueManager(config.as_dict(), self.history)
        self.qm.on_progress = self._on_progress
        self.qm.on_status = self._on_status
        self.qm.on_list_changed = self._on_list_changed
        self.qm.on_complete = self._on_complete
        self.scheduler = Scheduler(self.qm)
        if config.get("scheduler_enabled", False):
            self.scheduler.start()
        self.browser_server = BrowserIntegrationServer(self.qm, port=config.get("server_port", 9527))
        self.browser_server.start()

        # UI state
        self.rows = {}
        self.current_category = "all"
        self._quit_flag = False

        # Build UI
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_status_bar()

        # System tray
        self.tray = SystemTray(
            on_show=self._tray_show,
            on_add_url=self._add_url,
            on_pause_all=self._pause_all,
            on_resume_all=self._resume_all,
            on_quit=self._quit_from_tray,
        )
        if config.get("minimize_to_tray", True):
            self.tray.start()

        # Clipboard monitor
        self.clipboard = ClipboardMonitor(on_url=self._on_clipboard_url)
        if config.get("clipboard_monitor", True):
            self.clipboard.start()

        # First-run extension install
        self._maybe_auto_install_extensions()

        # Periodic refresh
        self.after(500, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------------------------------------------------------
    # Menu bar
    # ---------------------------------------------------------------
    def _build_menu(self):
        menubar = ctk.CTkFrame(self, height=24, fg_color="#1a1a1a", corner_radius=0)
        menubar.pack(side="top", fill="x")
        ctk.CTkButton(menubar, text="Tasks", width=60, height=22, fg_color="transparent",
                      hover_color="#2a2a2a", text_color="#ccc",
                      font=ctk.CTkFont(size=11),
                      command=self._menu_tasks).pack(side="left", padx=2)
        ctk.CTkButton(menubar, text="Downloads", width=80, height=22, fg_color="transparent",
                      hover_color="#2a2a2a", text_color="#ccc",
                      font=ctk.CTkFont(size=11),
                      command=self._menu_downloads).pack(side="left", padx=2)
        ctk.CTkButton(menubar, text="View", width=60, height=22, fg_color="transparent",
                      hover_color="#2a2a2a", text_color="#ccc",
                      font=ctk.CTkFont(size=11),
                      command=self._menu_view).pack(side="left", padx=2)
        ctk.CTkButton(menubar, text="Help", width=60, height=22, fg_color="transparent",
                      hover_color="#2a2a2a", text_color="#ccc",
                      font=ctk.CTkFont(size=11),
                      command=self._menu_help).pack(side="left", padx=2)

    def _menu_tasks(self):
        menu = ctk.CTkToplevel(self)
        menu.geometry(f"+{self.winfo_rootx()+10}+{self.winfo_rooty()+50}")
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        items = [("Add URL...", self._add_url),
                 ("Add Batch...", self._add_batch),
                 ("Site Grabber...", self._open_grabber),
                 ("Video Grabber...", self._open_video_grabber),
                 ("Exit", self._on_close)]
        for label, cmd in items:
            ctk.CTkButton(menu, text=label, width=180, height=28, anchor="w",
                          fg_color="transparent", hover_color="#333",
                          text_color="#eee",
                          command=lambda c=cmd, m=menu: (m.destroy(), c())).pack(fill="x")
        menu.focus_force()
        menu.bind("<FocusOut>", lambda e: menu.destroy())

    def _menu_downloads(self):
        menu = ctk.CTkToplevel(self)
        menu.geometry(f"+{self.winfo_rootx()+70}+{self.winfo_rooty()+50}")
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        items = [("Resume All", self._resume_all),
                 ("Pause All", self._pause_all),
                 ("Stop All", self._stop_all),
                 ("Scheduler...", self._open_scheduler),
                 ("Browser Extensions...", self._open_extensions),
                 ("Options...", self._open_settings)]
        for label, cmd in items:
            ctk.CTkButton(menu, text=label, width=200, height=28, anchor="w",
                          fg_color="transparent", hover_color="#333",
                          text_color="#eee",
                          command=lambda c=cmd, m=menu: (m.destroy(), c())).pack(fill="x")
        menu.focus_force()
        menu.bind("<FocusOut>", lambda e: menu.destroy())

    def _menu_view(self):
        menu = ctk.CTkToplevel(self)
        menu.geometry(f"+{self.winfo_rootx()+140}+{self.winfo_rooty()+50}")
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        items = [("Toggle Speed Graph", self._toggle_speed_graph),
                 ("Open Download Folder", self._open_folder),
                 ("Clear Completed", self._clear_completed)]
        for label, cmd in items:
            ctk.CTkButton(menu, text=label, width=220, height=28, anchor="w",
                          fg_color="transparent", hover_color="#333",
                          text_color="#eee",
                          command=lambda c=cmd, m=menu: (m.destroy(), c())).pack(fill="x")
        menu.focus_force()
        menu.bind("<FocusOut>", lambda e: menu.destroy())

    def _menu_help(self):
        messagebox.showinfo("About " + APP_NAME,
            f"{APP_NAME} v{APP_VERSION}\n\n"
            f"High-speed download manager for Windows 10/11 (64-bit)\n\n"
            f"Features:\n"
            f"  • 16-segment parallel downloads\n"
            f"  • Auto browser extension install (Chrome/Edge/Brave/Opera/Firefox)\n"
            f"  • Video Grabber (YouTube/Vimeo/TikTok/1000+ sites)\n"
            f"  • Site Grabber\n"
            f"  • Categories, Scheduler, Clipboard monitor\n"
            f"  • System tray, Sound notifications\n\n"
            f"Built with Python, CustomTkinter, requests, yt-dlp",
            parent=self)

    # ---------------------------------------------------------------
    # Toolbar
    # ---------------------------------------------------------------
    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, height=54, fg_color="#1a1a1a", corner_radius=0)
        tb.pack(side="top", fill="x")
        # Each button: emoji + label
        def tb_button(text, cmd, color=None):
            b = ctk.CTkButton(tb, text=text, width=92, height=38,
                              font=ctk.CTkFont(size=11),
                              fg_color=color or "#2a2a2a",
                              hover_color=color and ACCENT_HOVER or "#3a3a3a",
                              command=cmd)
            b.pack(side="left", padx=3, pady=8)
            return b
        tb_button("➕\nAdd URL", self._add_url, ACCENT)
        tb_button("▶\nResume", self._resume_all, "#0a8a3a")
        tb_button("⏸\nPause", self._pause_all, "#7a5a1f")
        tb_button("⏹\nStop All", self._stop_all, DANGER)
        tb_button("🗑\nClear Done", self._clear_completed, "#444")
        tb_button("🕸\nGrabber", self._open_grabber, "#3a4a8a")
        tb_button("🎬\nVideo", self._open_video_grabber, "#5a3a8a")
        tb_button("📅\nScheduler", self._open_scheduler, "#444")
        tb_button("🧩\nBrowser Ext", self._open_extensions, "#444")
        tb_button("⚙\nOptions", self._open_settings, "#444")

    # ---------------------------------------------------------------
    # Body: sidebar + main + speed graph
    # ---------------------------------------------------------------
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="top", fill="both", expand=True)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Sidebar
        sidebar = ctk.CTkScrollableFrame(body, width=210, fg_color="#1a1a1a",
                                         label_text="")
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 4))
        # Brand
        ctk.CTkLabel(sidebar, text=APP_NAME, anchor="w",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=ACCENT).pack(padx=12, pady=(12, 0), anchor="w")
        ctk.CTkLabel(sidebar, text=f"v{APP_VERSION}", anchor="w",
                     font=ctk.CTkFont(size=10), text_color="#777").pack(padx=12, pady=(0, 12), anchor="w")
        ctk.CTkLabel(sidebar, text="CATEGORIES", anchor="w",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#888").pack(padx=12, pady=(4, 6), anchor="w")
        self.cat_buttons = {}
        # Virtual categories
        for cid, name, icon, color in VIRTUAL_CATEGORIES:
            self._add_cat_button(sidebar, cid, f"{icon}  {name}", color)
        # File-type categories
        ctk.CTkLabel(sidebar, text="FILE TYPES", anchor="w",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#888").pack(padx=12, pady=(12, 6), anchor="w")
        for cid, name, icon, _, color in CATEGORIES:
            self._add_cat_button(sidebar, cid, f"{icon}  {name}", color)
        self._highlight_category()
        # Footer in sidebar
        ctk.CTkButton(sidebar, text="📂  Open Folder", width=180, height=30,
                      fg_color="#2a2a2a", hover_color="#3a3a3a",
                      command=self._open_folder).pack(padx=12, pady=(15, 8), fill="x")

        # Main area: download list + speed graph
        main = ctk.CTkFrame(body, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # List header
        header = ctk.CTkFrame(main, height=22, fg_color="#222", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="File Name / Status", anchor="w",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#888").grid(row=0, column=0, sticky="w", padx=12)
        ctk.CTkLabel(header, text="Size      Speed      ETA", anchor="e",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#888", width=220).grid(row=0, column=1, sticky="e", padx=12)

        # Scrollable download list
        self.list_wrap = ctk.CTkScrollableFrame(main, fg_color="transparent",
                                                label_text="")
        self.list_wrap.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self.list_wrap.grid_columnconfigure(0, weight=1)

        # Speed graph (bottom)
        graph_row = ctk.CTkFrame(main, fg_color="transparent")
        graph_row.grid(row=2, column=0, sticky="ew", padx=2, pady=(4, 2))
        graph_row.grid_columnconfigure(0, weight=1)
        self.speed_graph = SpeedGraph(graph_row, width=900, height=80)
        self.speed_graph.grid(row=0, column=0, sticky="ew", padx=2)
        if not config.get("show_speed_graph", True):
            self.speed_graph.grid_remove()

    def _add_cat_button(self, sidebar, cid, label, color):
        btn = ctk.CTkButton(sidebar, text=label, anchor="w", height=30,
                            fg_color="transparent", hover_color="#2a2a2a",
                            text_color="#ddd",
                            font=ctk.CTkFont(size=12),
                            command=lambda c=cid: self._set_category(c))
        btn.pack(fill="x", padx=8, pady=2)
        self.cat_buttons[cid] = (btn, color)

    def _highlight_category(self):
        for cid, (btn, color) in self.cat_buttons.items():
            if cid == self.current_category:
                btn.configure(fg_color=color, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="#ddd")

    def _set_category(self, cid):
        self.current_category = cid
        self._highlight_category()
        self._rebuild_rows()

    # ---------------------------------------------------------------
    # Status bar
    # ---------------------------------------------------------------
    def _build_status_bar(self):
        sb = ctk.CTkFrame(self, height=26, fg_color="#111", corner_radius=0)
        sb.pack(side="bottom", fill="x")
        self.sb_speed = ctk.CTkLabel(sb, text="Speed: 0 KB/s", anchor="w", text_color="#aaa",
                                     font=ctk.CTkFont(size=10))
        self.sb_speed.pack(side="left", padx=12)
        self.sb_active = ctk.CTkLabel(sb, text="Active: 0", anchor="w", text_color="#aaa",
                                      font=ctk.CTkFont(size=10))
        self.sb_active.pack(side="left", padx=12)
        self.sb_queue = ctk.CTkLabel(sb, text="Queued: 0", anchor="w", text_color="#aaa",
                                     font=ctk.CTkFont(size=10))
        self.sb_queue.pack(side="left", padx=12)
        ctk.CTkLabel(sb, text=f"{APP_NAME} v{APP_VERSION}", anchor="e",
                     text_color=ACCENT, font=ctk.CTkFont(size=10)).pack(side="right", padx=12)

    # ---------------------------------------------------------------
    # Toolbar actions
    # ---------------------------------------------------------------
    def _add_url(self):
        AddURLDialog(self, self._on_add_url_ok)

    def _on_add_url_ok(self, url, name, auto_start, category, folder):
        # Override folder if user changed it
        if folder and folder != config.get("download_folder"):
            cfg = config.as_dict()
            cfg["download_folder"] = folder
            self.qm.update_config(cfg)
        self.qm.add(url, name, auto_start=auto_start)
        if config.get("sound_on_complete"):
            try: sounds.play_added()
            except: pass

    def _add_batch(self):
        BatchDownloadDialog(self, self._on_add_url_ok)

    def _open_grabber(self):
        SiteGrabberDialog(self, self._on_add_url_ok)

    def _open_video_grabber(self):
        VideoGrabberDialog(self, config.as_dict())

    def _open_scheduler(self):
        SchedulerDialog(self, config.as_dict(), self._on_scheduler_save)

    def _on_scheduler_save(self, new_cfg):
        config.update(new_cfg)
        self.scheduler.stop()
        if config.get("scheduler_enabled", False):
            self.scheduler = Scheduler(self.qm)
            self.scheduler.start()
        messagebox.showinfo("Saved", "Scheduler settings saved.", parent=self)

    def _open_extensions(self):
        BrowserExtensionsDialog(self)

    def _open_settings(self):
        SettingsDialog(self, config.as_dict(), self._on_settings_save)

    def _on_settings_save(self, new_cfg):
        config.update(new_cfg)
        ctk.set_appearance_mode(config.get("appearance", "dark"))
        self.qm.update_config(config.as_dict())
        if self.browser_server.port != config.get("server_port", 9527):
            self.browser_server.stop()
            self.browser_server = BrowserIntegrationServer(self.qm, port=config.get("server_port", 9527))
            self.browser_server.start()
        self.scheduler.stop()
        if config.get("scheduler_enabled", False):
            self.scheduler = Scheduler(self.qm)
            self.scheduler.start()
        # Toggle speed graph visibility
        if config.get("show_speed_graph", True):
            self.speed_graph.grid()
        else:
            self.speed_graph.grid_remove()
        # Clipboard
        if config.get("clipboard_monitor", True):
            self.clipboard.start()
        else:
            self.clipboard.stop()
        messagebox.showinfo("Saved", "Settings saved.", parent=self)

    def _resume_all(self):
        self.qm.start_all()

    def _pause_all(self):
        self.qm.pause_all()

    def _stop_all(self):
        self.qm.stop_all()

    def _clear_completed(self):
        self.qm.clear_completed()

    def _toggle_speed_graph(self):
        cur = config.get("show_speed_graph", True)
        config.set("show_speed_graph", not cur)
        if config.get("show_speed_graph"):
            self.speed_graph.grid()
        else:
            self.speed_graph.grid_remove()

    def _open_folder(self):
        folder = config.get("download_folder", os.path.expanduser("~/Downloads"))
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Open folder", str(e), parent=self)

    # ---------------------------------------------------------------
    # Row actions
    # ---------------------------------------------------------------
    def _on_row_pause(self, task): self.qm.pause(task)
    def _on_row_resume(self, task): self.qm.start(task)
    def _on_row_stop(self, task): self.qm.stop(task)
    def _on_row_remove(self, task):
        if messagebox.askyesno("Remove", f"Remove '{task.file_name}'?", parent=self):
            self.qm.remove(task, delete_files=False)
    def _on_row_open(self, task):
        if task.status != STATUS_COMPLETE:
            messagebox.showinfo("Open", "File is not complete yet.", parent=self)
            return
        try:
            if sys.platform == "win32":
                os.startfile(task.file_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", task.file_path])
            else:
                subprocess.Popen(["xdg-open", task.file_path])
        except Exception as e:
            messagebox.showerror("Open", str(e), parent=self)

    # ---------------------------------------------------------------
    # Queue callbacks
    # ---------------------------------------------------------------
    def _on_list_changed(self):
        self.after(0, self._rebuild_rows)

    def _on_progress(self, task):
        self.after(0, lambda t=task: self._refresh_row(t))

    def _on_status(self, task):
        self.after(0, lambda t=task: self._refresh_row(t))

    def _on_complete(self, task):
        # Sound
        if config.get("sound_on_complete", True):
            try: sounds.play_complete()
            except: pass
        # Antivirus scan
        if config.get("antivirus_scan", False):
            def _scan():
                from antivirus import scan_file
                clean, msg = scan_file(task.file_path)
                if not clean:
                    self.after(0, lambda: messagebox.showwarning(
                        "Antivirus Warning",
                        f"File: {task.file_name}\n\n{msg}", parent=self))
            threading.Thread(target=_scan, daemon=True).start()
        # Auto-shutdown if scheduler + no more active
        if config.get("scheduler_auto_shutdown", False):
            if self.qm.active_count() == 0 and self.qm.queue_count() == 0:
                if sys.platform == "win32":
                    try:
                        subprocess.Popen(["shutdown", "/s", "/t", "60"])
                    except Exception:
                        pass

    def _on_clipboard_url(self, url):
        """Called from clipboard monitor when a download URL is detected."""
        # Show a non-blocking popup asking the user
        def _ask():
            if messagebox.askyesno("Add Download?",
                f"A download URL was detected on your clipboard:\n\n{url}\n\n"
                f"Add it to the download queue?", parent=self):
                self.qm.add(url, "", auto_start=config.get("auto_start", True))
        self.after(0, _ask)

    # ---------------------------------------------------------------
    # Row rendering
    # ---------------------------------------------------------------
    def _category_filter(self, t):
        if self.current_category == "all":
            return True
        if self.current_category == "unfinished":
            return t.status != STATUS_COMPLETE
        if self.current_category == "finished":
            return t.status == STATUS_COMPLETE
        # File-type category
        return get_category_id(t.file_name or "") == self.current_category

    def _rebuild_rows(self):
        for child in self.list_wrap.winfo_children():
            child.destroy()
        self.rows.clear()
        for task in self.qm.tasks:
            if not self._category_filter(task):
                continue
            row = DownloadRow(self.list_wrap, task,
                              on_pause=self._on_row_pause,
                              on_resume=self._on_row_resume,
                              on_stop=self._on_row_stop,
                              on_remove=self._on_row_remove,
                              on_open=self._on_row_open)
            row.grid(sticky="ew", pady=3)
            self.rows[id(task)] = row
        self._update_status_bar()

    def _refresh_row(self, task):
        row = self.rows.get(id(task))
        if row:
            row.refresh()
        if not self._category_filter(task):
            self._rebuild_rows()
        self._update_status_bar()

    def _update_status_bar(self):
        self.sb_speed.configure(text=f"Speed: {human_speed(self.qm.total_speed_kbps())}")
        self.sb_active.configure(text=f"Active: {self.qm.active_count()}")
        self.sb_queue.configure(text=f"Queued: {self.qm.queue_count()}")
        # Tray tooltip
        if hasattr(self, "tray") and self.tray:
            self.tray.update_tooltip(
                f"{APP_NAME} - Active: {self.qm.active_count()}, Speed: {human_speed(self.qm.total_speed_kbps())}")

    # ---------------------------------------------------------------
    # Periodic tick
    # ---------------------------------------------------------------
    def _tick(self):
        for task in self.qm.tasks:
            if task.status in (STATUS_DOWNLOADING, STATUS_PAUSED):
                row = self.rows.get(id(task))
                if row:
                    row.refresh()
        # Update speed graph
        self.speed_graph.add_point(self.qm.total_speed_kbps())
        self._update_status_bar()
        self.after(500, self._tick)

    # ---------------------------------------------------------------
    # Tray / close handling
    # ---------------------------------------------------------------
    def _tray_show(self):
        self.after(0, lambda: (self.deiconify(), self.lift(), self.focus_force()))

    def _quit_from_tray(self):
        self._quit_flag = True
        self.after(0, self._on_close)

    def _on_close(self):
        if not self._quit_flag and config.get("minimize_to_tray", True):
            # Minimize to tray instead of quitting
            self.withdraw()
            return
        # Real quit
        try:
            self.qm.pause_all()
            self.scheduler.stop()
            self.browser_server.stop()
            self.clipboard.stop()
            self.tray.stop()
        except Exception:
            pass
        try:
            w, h = self.winfo_width(), self.winfo_height()
            if w > 100 and h > 100:
                config.set("window_size", f"{w}x{h}")
        except Exception:
            pass
        self.destroy()

    # ---------------------------------------------------------------
    # First-run auto extension install
    # ---------------------------------------------------------------
    def _maybe_auto_install_extensions(self):
        if config.get("extensions_installed", False):
            return
        def _work():
            try:
                from extension_installer import install_for_all_browsers
                install_for_all_browsers()
                config.set("extensions_installed", True)
            except Exception as e:
                print(f"[AutoInstall] error: {e}")
        threading.Thread(target=_work, daemon=True).start()
