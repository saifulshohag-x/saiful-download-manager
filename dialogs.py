"""
dialogs.py - IDM-style dialogs for Saiful Download Manager.

Add URL, Add Batch, Settings (tabbed), Scheduler, Video Grabber, Site Grabber,
Browser Extensions installer.
"""
import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from youtube_grabber import YouTubeGrabber
from config import APP_NAME, APP_VERSION
from categories import CATEGORIES, VIRTUAL_CATEGORIES
from batch_download import expand_pattern


# ---------------------------------------------------------------------------
# Add URL dialog (IDM-style)
# ---------------------------------------------------------------------------
class AddURLDialog(ctk.CTkToplevel):
    def __init__(self, master, on_ok, default_url: str = ""):
        super().__init__(master)
        self.title("Add URL")
        self.geometry("560x420")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_ok = on_ok

        ctk.CTkLabel(self, text="Address:", anchor="w").pack(
            padx=20, pady=(20, 5), anchor="w", fill="x")
        self.url_entry = ctk.CTkEntry(self, placeholder_text="https://...")
        self.url_entry.pack(padx=20, pady=2, fill="x")
        if default_url:
            self.url_entry.insert(0, default_url)

        ctk.CTkLabel(self, text="File name (optional):", anchor="w").pack(
            padx=20, pady=(10, 5), anchor="w", fill="x")
        self.name_entry = ctk.CTkEntry(self,
            placeholder_text="leave blank to use server filename")
        self.name_entry.pack(padx=20, pady=2, fill="x")

        ctk.CTkLabel(self, text="Save to folder:", anchor="w").pack(
            padx=20, pady=(10, 5), anchor="w", fill="x")
        folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        folder_frame.pack(padx=20, pady=2, fill="x")
        self.folder_entry = ctk.CTkEntry(folder_frame)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(folder_frame, text="Browse", width=80,
                      command=self._browse).pack(side="left")
        from config import config
        self.folder_entry.insert(0, config.get("download_folder", ""))

        ctk.CTkLabel(self, text="Category:", anchor="w").pack(
            padx=20, pady=(10, 5), anchor="w", fill="x")
        self.cat_var = ctk.StringVar(value="Auto-detect")
        cat_values = ["Auto-detect"] + [c[1] for c in CATEGORIES]
        ctk.CTkOptionMenu(self, variable=self.cat_var, values=cat_values,
                          width=200).pack(padx=20, pady=2, anchor="w")

        # Start mode
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(padx=20, pady=(15, 5), fill="x")
        self.mode_var = ctk.StringVar(value="start_now")
        ctk.CTkRadioButton(mode_frame, text="Start download now",
                           variable=self.mode_var, value="start_now").pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(mode_frame, text="Add to queue only",
                           variable=self.mode_var, value="queue").pack(side="left")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancel", width=100,
                      command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Start Download", width=140,
                      command=self._ok).pack(side="left", padx=10)
        self.url_entry.bind("<Return>", lambda e: self._ok())
        self.name_entry.bind("<Return>", lambda e: self._ok())

    def _browse(self):
        d = filedialog.askdirectory(parent=self, initialdir=self.folder_entry.get())
        if d:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, d)

    def _ok(self):
        url = self.url_entry.get().strip()
        name = self.name_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a URL.", parent=self)
            return
        auto_start = (self.mode_var.get() == "start_now")
        self.on_ok(url, name, auto_start, self.cat_var.get(),
                   self.folder_entry.get().strip())
        self.destroy()


# ---------------------------------------------------------------------------
# Batch download dialog
# ---------------------------------------------------------------------------
class BatchDownloadDialog(ctk.CTkToplevel):
    def __init__(self, master, on_add):
        super().__init__(master)
        self.title("Add Batch Download")
        self.geometry("600x340")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_add = on_add

        ctk.CTkLabel(self,
            text="URL pattern (use [start-end] for ranges):",
            anchor="w").pack(padx=20, pady=(20, 5), anchor="w", fill="x")
        self.url_entry = ctk.CTkEntry(self,
            placeholder_text='e.g. https://example.com/file[01-10].zip')
        self.url_entry.pack(padx=20, pady=2, fill="x")

        ctk.CTkButton(self, text="Preview", width=100,
                      command=self._preview).pack(padx=20, pady=10, anchor="w")

        ctk.CTkLabel(self, text="Expanded URLs:", anchor="w").pack(
            padx=20, pady=(5, 5), anchor="w", fill="x")
        self.listbox = ctk.CTkTextbox(self, height=140, state="disabled")
        self.listbox.pack(padx=20, pady=2, fill="both", expand=True)

        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(pady=15)
        ctk.CTkButton(btn, text="Cancel", width=100,
                      command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn, text="Add All", width=120,
                      command=self._add).pack(side="left", padx=10)

    def _preview(self):
        pat = self.url_entry.get().strip()
        if not pat:
            return
        urls = expand_pattern(pat)
        self.listbox.configure(state="normal")
        self.listbox.delete("1.0", "end")
        for u in urls:
            self.listbox.insert("end", u + "\n")
        self.listbox.configure(state="disabled")
        self.listbox.see("end")

    def _add(self):
        pat = self.url_entry.get().strip()
        if not pat:
            return
        urls = expand_pattern(pat)
        for u in urls:
            self.on_add(u, "", True, "Auto-detect", "")
        self.destroy()


# ---------------------------------------------------------------------------
# Settings dialog (tabbed)
# ---------------------------------------------------------------------------
class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, cfg: dict, on_save):
        super().__init__(master)
        self.title(f"{APP_NAME} - Options")
        self.geometry("620x640")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.cfg = dict(cfg)
        self.on_save = on_save

        self.tabview = ctk.CTkTabview(self, width=580)
        self.tabview.pack(padx=15, pady=15, fill="both", expand=True)
        self.tab_general = self.tabview.add("General")
        self.tab_connection = self.tabview.add("Connection")
        self.tab_scheduler = self.tabview.add("Scheduler")
        self.tab_sound = self.tabview.add("Sounds/Tray")
        self._build_general()
        self._build_connection()
        self._build_scheduler()
        self._build_sound()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Cancel", width=100,
                      command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Save", width=100,
                      command=self._save).pack(side="left", padx=10)

    def _build_general(self):
        t = self.tab_general
        ctk.CTkLabel(t, text="Default download folder:").pack(padx=10, pady=(15, 5), anchor="w")
        ff = ctk.CTkFrame(t, fg_color="transparent")
        ff.pack(padx=10, fill="x")
        self.folder_entry = ctk.CTkEntry(ff, width=440)
        self.folder_entry.insert(0, self.cfg.get("download_folder", ""))
        self.folder_entry.pack(side="left", padx=(0, 8), fill="x", expand=True)
        ctk.CTkButton(ff, text="Browse", width=80,
                      command=self._browse_folder).pack(side="left")

        self.cat_var = ctk.BooleanVar(value=bool(self.cfg.get("categories_enabled", True)))
        ctk.CTkCheckBox(t, text="Enable file-type categories (Compressed/Documents/Music/...)",
                        variable=self.cat_var).pack(padx=10, pady=(15, 0), anchor="w")
        self.subfolder_var = ctk.BooleanVar(value=bool(self.cfg.get("category_folders", True)))
        ctk.CTkCheckBox(t, text="Save each category into its own subfolder",
                        variable=self.subfolder_var).pack(padx=10, pady=(5, 0), anchor="w")

        self.cb_var = ctk.BooleanVar(value=bool(self.cfg.get("clipboard_monitor", True)))
        ctk.CTkCheckBox(t, text="Monitor clipboard for download URLs",
                        variable=self.cb_var).pack(padx=10, pady=(15, 0), anchor="w")

        self.theme_var = ctk.StringVar(value=self.cfg.get("appearance", "dark"))
        ctk.CTkLabel(t, text="Appearance:").pack(padx=10, pady=(15, 5), anchor="w")
        ctk.CTkSegmentedButton(t, values=["dark", "light", "system"],
                               variable=self.theme_var).pack(padx=10, anchor="w")

    def _build_connection(self):
        t = self.tab_connection
        ctk.CTkLabel(t, text="Connections per download (1-32):").pack(padx=10, pady=(15, 5), anchor="w")
        self.segments_var = ctk.IntVar(value=int(self.cfg.get("segments", 16)))
        ctk.CTkSlider(t, from_=1, to=32, variable=self.segments_var,
                      number_of_steps=31).pack(padx=10, fill="x")
        self.seg_label = ctk.CTkLabel(t, text=str(self.segments_var.get()))
        self.seg_label.pack()
        self.segments_var.trace_add("write", lambda *_: self.seg_label.configure(
            text=str(self.segments_var.get())))

        ctk.CTkLabel(t, text="Max concurrent downloads (1-10):").pack(padx=10, pady=(15, 5), anchor="w")
        self.cc_var = ctk.IntVar(value=int(self.cfg.get("max_concurrent", 5)))
        ctk.CTkSlider(t, from_=1, to=10, variable=self.cc_var,
                      number_of_steps=9).pack(padx=10, fill="x")
        self.cc_label = ctk.CTkLabel(t, text=str(self.cc_var.get()))
        self.cc_label.pack()
        self.cc_var.trace_add("write", lambda *_: self.cc_label.configure(
            text=str(self.cc_var.get())))

        ctk.CTkLabel(t, text="Speed limit (KB/s, 0 = unlimited):").pack(padx=10, pady=(15, 5), anchor="w")
        self.speed_entry = ctk.CTkEntry(t, width=200)
        self.speed_entry.insert(0, str(self.cfg.get("speed_limit_kbps", 0)))
        self.speed_entry.pack(padx=10, anchor="w")

        ctk.CTkLabel(t, text="Browser integration port:").pack(padx=10, pady=(15, 5), anchor="w")
        self.port_entry = ctk.CTkEntry(t, width=120)
        self.port_entry.insert(0, str(self.cfg.get("server_port", 9527)))
        self.port_entry.pack(padx=10, anchor="w")

    def _build_scheduler(self):
        t = self.tab_scheduler
        self.sched_var = ctk.BooleanVar(value=bool(self.cfg.get("scheduler_enabled", False)))
        ctk.CTkCheckBox(t, text="Enable scheduler (auto start/stop downloads)",
                        variable=self.sched_var).pack(padx=10, pady=(15, 0), anchor="w")
        time_frame = ctk.CTkFrame(t, fg_color="transparent")
        time_frame.pack(padx=10, pady=10, fill="x")
        ctk.CTkLabel(time_frame, text="Start time (HH:MM):").pack(side="left", padx=(0, 5))
        self.start_entry = ctk.CTkEntry(time_frame, width=70)
        self.start_entry.insert(0, self.cfg.get("scheduler_start", "00:00"))
        self.start_entry.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(time_frame, text="Stop time (HH:MM):").pack(side="left", padx=(0, 5))
        self.stop_entry = ctk.CTkEntry(time_frame, width=70)
        self.stop_entry.insert(0, self.cfg.get("scheduler_stop", "23:59"))
        self.stop_entry.pack(side="left")

        ctk.CTkLabel(t, text="Days of week:").pack(padx=10, pady=(15, 5), anchor="w")
        days_frame = ctk.CTkFrame(t, fg_color="transparent")
        days_frame.pack(padx=10, fill="x")
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.day_vars = []
        cur_days = set(self.cfg.get("scheduler_days", [1, 2, 3, 4, 5, 6, 7]))
        for i, d in enumerate(days, 1):
            v = ctk.BooleanVar(value=(i in cur_days))
            self.day_vars.append(v)
            ctk.CTkCheckBox(days_frame, text=d, variable=v).pack(side="left", padx=4)

        self.shutdown_var = ctk.BooleanVar(value=bool(self.cfg.get("scheduler_auto_shutdown", False)))
        ctk.CTkCheckBox(t, text="Auto-shutdown PC when all downloads complete",
                        variable=self.shutdown_var).pack(padx=10, pady=(20, 0), anchor="w")

    def _build_sound(self):
        t = self.tab_sound
        self.sound_complete_var = ctk.BooleanVar(value=bool(self.cfg.get("sound_on_complete", True)))
        ctk.CTkCheckBox(t, text="Play sound on download complete",
                        variable=self.sound_complete_var).pack(padx=10, pady=(15, 0), anchor="w")
        self.sound_error_var = ctk.BooleanVar(value=bool(self.cfg.get("sound_on_error", False)))
        ctk.CTkCheckBox(t, text="Play sound on download error",
                        variable=self.sound_error_var).pack(padx=10, pady=(5, 0), anchor="w")

        self.tray_var = ctk.BooleanVar(value=bool(self.cfg.get("minimize_to_tray", True)))
        ctk.CTkCheckBox(t, text="Minimize to system tray instead of taskbar",
                        variable=self.tray_var).pack(padx=10, pady=(20, 0), anchor="w")

        self.graph_var = ctk.BooleanVar(value=bool(self.cfg.get("show_speed_graph", True)))
        ctk.CTkCheckBox(t, text="Show speed graph in main window",
                        variable=self.graph_var).pack(padx=10, pady=(5, 0), anchor="w")

        self.av_var = ctk.BooleanVar(value=bool(self.cfg.get("antivirus_scan", False)))
        ctk.CTkCheckBox(t, text="Scan completed files with Windows Defender",
                        variable=self.av_var).pack(padx=10, pady=(5, 0), anchor="w")

    def _browse_folder(self):
        d = filedialog.askdirectory(parent=self, initialdir=self.folder_entry.get())
        if d:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, d)

    def _save(self):
        try: speed = int(self.speed_entry.get().strip() or "0")
        except ValueError: speed = 0
        try: port = int(self.port_entry.get().strip() or "9527")
        except ValueError: port = 9527
        days = [i + 1 for i, v in enumerate(self.day_vars) if v.get()]
        new_cfg = {
            "download_folder": self.folder_entry.get().strip(),
            "categories_enabled": bool(self.cat_var.get()),
            "category_folders": bool(self.subfolder_var.get()),
            "clipboard_monitor": bool(self.cb_var.get()),
            "appearance": self.theme_var.get(),
            "theme": "Dark" if self.theme_var.get() == "dark" else "Light",
            "segments": int(self.segments_var.get()),
            "max_concurrent": int(self.cc_var.get()),
            "speed_limit_kbps": max(0, speed),
            "server_port": max(1024, min(65535, port)),
            "scheduler_enabled": bool(self.sched_var.get()),
            "scheduler_start": self.start_entry.get().strip() or "00:00",
            "scheduler_stop": self.stop_entry.get().strip() or "23:59",
            "scheduler_days": days,
            "scheduler_auto_shutdown": bool(self.shutdown_var.get()),
            "sound_on_complete": bool(self.sound_complete_var.get()),
            "sound_on_error": bool(self.sound_error_var.get()),
            "minimize_to_tray": bool(self.tray_var.get()),
            "show_speed_graph": bool(self.graph_var.get()),
            "antivirus_scan": bool(self.av_var.get()),
        }
        self.on_save(new_cfg)
        self.destroy()


# ---------------------------------------------------------------------------
# Scheduler dialog (quick toggle)
# ---------------------------------------------------------------------------
class SchedulerDialog(ctk.CTkToplevel):
    def __init__(self, master, cfg: dict, on_save):
        super().__init__(master)
        self.title("Scheduler")
        self.geometry("480x300")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.cfg = dict(cfg)
        self.on_save = on_save

        self.enabled_var = ctk.BooleanVar(value=bool(cfg.get("scheduler_enabled", False)))
        ctk.CTkCheckBox(self, text="Enable download scheduler",
                        variable=self.enabled_var).pack(padx=20, pady=(20, 10), anchor="w")
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(padx=20, fill="x")
        ctk.CTkLabel(f, text="Start:").pack(side="left", padx=(0, 5))
        self.start_e = ctk.CTkEntry(f, width=80)
        self.start_e.insert(0, cfg.get("scheduler_start", "00:00"))
        self.start_e.pack(side="left", padx=(0, 25))
        ctk.CTkLabel(f, text="Stop:").pack(side="left", padx=(0, 5))
        self.stop_e = ctk.CTkEntry(f, width=80)
        self.stop_e.insert(0, cfg.get("scheduler_stop", "23:59"))
        self.stop_e.pack(side="left")
        self.shutdown_var = ctk.BooleanVar(value=bool(cfg.get("scheduler_auto_shutdown", False)))
        ctk.CTkCheckBox(self, text="Auto-shutdown when all downloads complete",
                        variable=self.shutdown_var).pack(padx=20, pady=(20, 0), anchor="w")
        b = ctk.CTkFrame(self, fg_color="transparent")
        b.pack(pady=20)
        ctk.CTkButton(b, text="Cancel", width=100, command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(b, text="Save", width=100, command=self._save).pack(side="left", padx=10)

    def _save(self):
        self.on_save({
            "scheduler_enabled": bool(self.enabled_var.get()),
            "scheduler_start": self.start_e.get().strip() or "00:00",
            "scheduler_stop": self.stop_e.get().strip() or "23:59",
            "scheduler_auto_shutdown": bool(self.shutdown_var.get()),
        })
        self.destroy()


# ---------------------------------------------------------------------------
# Browser Extensions installer dialog
# ---------------------------------------------------------------------------
class BrowserExtensionsDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Install Browser Extensions")
        self.geometry("640x520")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        ctk.CTkLabel(self, text="Auto-install extension for Chrome, Edge, Brave, Opera, Firefox",
                     anchor="w").pack(padx=20, pady=(20, 5), anchor="w")
        ctk.CTkLabel(self, text="Click the button. We'll detect each browser and install.",
                     text_color="#aaa", anchor="w").pack(padx=20, pady=(0, 15), anchor="w")

        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(pady=5)
        self.install_btn = ctk.CTkButton(btn, text="Detect & Install",
                                         width=220, height=36,
                                         command=self._install)
        self.install_btn.pack()

        self.log = ctk.CTkTextbox(self, width=580, height=320, state="disabled")
        self.log.pack(padx=20, pady=15, fill="both", expand=True)
        ctk.CTkButton(self, text="Close", width=100, command=self.destroy).pack(pady=10)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _install(self):
        self.install_btn.configure(state="disabled", text="Installing...")
        self._log("Detecting browsers...")
        def _work():
            from extension_installer import install_for_all_browsers, detect_browsers
            browsers = detect_browsers()
            if not browsers:
                self.after(0, lambda: self._log("No browsers detected."))
                self.after(0, lambda: self.install_btn.configure(state="normal", text="Detect & Install"))
                return
            self.after(0, lambda: self._log(f"Found {len(browsers)} browser(s):"))
            for b in browsers:
                self.after(0, lambda b=b: self._log(f"  - {b['name']} ({b['engine']})"))
            self.after(0, lambda: self._log(""))
            self.after(0, lambda: self._log("Installing..."))
            result = install_for_all_browsers()
            for b in result["browsers"]:
                status = "OK" if b["success"] else "FAILED"
                self.after(0, lambda b=b, s=status: self._log(f"  [{s}] {b['name']}: {b['message']}"))
            self.after(0, lambda: self._log(""))
            self.after(0, lambda: self._log(result["summary"]))
            self.after(0, lambda: self._log("Tip: Restart your browser(s) to load the extension."))
            self.after(0, lambda: self.install_btn.configure(state="normal", text="Detect & Install"))
        threading.Thread(target=_work, daemon=True).start()


# ---------------------------------------------------------------------------
# Video Grabber dialog
# ---------------------------------------------------------------------------
class VideoGrabberDialog(ctk.CTkToplevel):
    def __init__(self, master, cfg: dict):
        super().__init__(master)
        self.title("Video Grabber (YouTube / Vimeo / etc.)")
        self.geometry("780x560")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.cfg = cfg
        self.grabber = YouTubeGrabber(cfg.get("download_folder", ""), cfg)
        self.formats = []

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(padx=15, pady=15, fill="x")
        ctk.CTkLabel(top, text="Video URL:").pack(side="left", padx=(0, 8))
        self.url_entry = ctk.CTkEntry(top, width=480,
            placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.pack(side="left", padx=(0, 8), fill="x", expand=True)
        self.fetch_btn = ctk.CTkButton(top, text="Fetch Formats", width=130, command=self._fetch)
        self.fetch_btn.pack(side="left")

        self.title_label = ctk.CTkLabel(self, text="", anchor="w")
        self.title_label.pack(padx=15, anchor="w")

        self.listbox = ctk.CTkTextbox(self, width=720, height=280, state="disabled")
        self.listbox.pack(padx=15, pady=10, fill="both", expand=True)

        self.progress = ctk.CTkProgressBar(self, width=720)
        self.progress.set(0)
        self.progress.pack(padx=15, pady=5, fill="x")
        self.status_label = ctk.CTkLabel(self, text="Ready")
        self.status_label.pack(padx=15, anchor="w")

        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(pady=10)
        ctk.CTkButton(btn, text="Close", width=100, command=self.destroy).pack(side="left", padx=10)
        self.dl_btn = ctk.CTkButton(btn, text="Download Selected", width=160,
                                    command=self._download, state="disabled")
        self.dl_btn.pack(side="left", padx=10)
        self._selected_idx = -1

    def _fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please paste a video URL.", parent=self)
            return
        self.fetch_btn.configure(state="disabled", text="Fetching...")
        self.title_label.configure(text="Fetching formats, please wait...")
        self.listbox.configure(state="normal")
        self.listbox.delete("1.0", "end")
        self.listbox.configure(state="disabled")
        def _cb(error, formats, title):
            self.after(0, lambda: self._on_fetch_done(error, formats, title))
        threading.Thread(target=self.grabber.list_formats, args=(url, _cb), daemon=True).start()

    def _on_fetch_done(self, error, formats, title):
        self.fetch_btn.configure(state="normal", text="Fetch Formats")
        if error:
            self.title_label.configure(text=f"Error: {error}")
            return
        self.formats = formats
        self.title_label.configure(text=f"Title: {title}    ({len(formats)} formats)")
        self.listbox.configure(state="normal")
        self.listbox.delete("1.0", "end")
        for i, f in enumerate(formats):
            self.listbox.insert("end", f"[{i:3d}] {f.label()}\n")
        self.listbox.configure(state="disabled")
        if formats:
            self.dl_btn.configure(state="normal")
            self._selected_idx = len(formats) - 1
            for i, f in enumerate(formats):
                if f.ext == "mp4" and f.vcodec != "none" and f.acodec != "none":
                    self._selected_idx = i
                    break
            self.status_label.configure(text=f"Default = #{self._selected_idx}. Click Download and enter format #.")
        else:
            self.dl_btn.configure(state="disabled")
            self.status_label.configure(text="No formats found.")

    def _download(self):
        idx_str = ctk.CTkInputDialog(text="Enter format # from the list above:",
                                     title="Format", default=str(self._selected_idx)).get_input()
        if idx_str is None:
            return
        try:
            idx = int(idx_str)
            fmt = self.formats[idx]
        except (ValueError, IndexError):
            messagebox.showerror("Invalid", "Please enter a valid format number.", parent=self)
            return
        url = self.url_entry.get().strip()
        if not url:
            return
        self.dl_btn.configure(state="disabled")
        self.progress.set(0)
        self.status_label.configure(text="Starting download...")
        def _on_progress(pct, speed, eta, status):
            self.after(0, lambda: self._update_progress(pct, speed, eta, status))
        def _on_done(error, filename):
            self.after(0, lambda: self._on_download_done(error, filename))
        self.grabber.download(url, fmt.format_id, fmt.ext,
                              on_progress=_on_progress, on_done=_on_done)

    def _update_progress(self, pct, speed, eta, status):
        self.progress.set(pct / 100.0)
        from download_engine import human_speed, eta_str
        self.status_label.configure(
            text=f"{status}  -  {pct:.1f}%  -  {human_speed(speed)}  -  ETA {eta_str(eta)}")

    def _on_download_done(self, error, filename):
        if error:
            self.status_label.configure(text=f"Error: {error}")
            messagebox.showerror("Download failed", str(error), parent=self)
        else:
            self.status_label.configure(text=f"Done: {filename}")
            self.progress.set(1.0)
            messagebox.showinfo("Complete", f"Saved: {filename}", parent=self)
        self.dl_btn.configure(state="normal")


# ---------------------------------------------------------------------------
# Site Grabber dialog
# ---------------------------------------------------------------------------
class SiteGrabberDialog(ctk.CTkToplevel):
    def __init__(self, master, on_download):
        super().__init__(master)
        self.title("Site Grabber")
        self.geometry("720x520")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_download = on_download
        self.results = []

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(padx=15, pady=15, fill="x")
        ctk.CTkLabel(top, text="Page URL:").pack(side="left", padx=(0, 8))
        self.url_entry = ctk.CTkEntry(top, width=420,
            placeholder_text="https://example.com/page.html")
        self.url_entry.pack(side="left", padx=(0, 8), fill="x", expand=True)
        self.btn = ctk.CTkButton(top, text="Grab", width=100, command=self._grab)
        self.btn.pack(side="left")

        self.listbox = ctk.CTkTextbox(self, width=680, height=350, state="disabled")
        self.listbox.pack(padx=15, pady=10, fill="both", expand=True)

        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(pady=10)
        ctk.CTkButton(btn, text="Close", width=100, command=self.destroy).pack(side="left", padx=10)
        self.dl_btn = ctk.CTkButton(btn, text="Download Selected", width=160,
                                    command=self._download, state="disabled")
        self.dl_btn.pack(side="left", padx=10)

    def _grab(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.btn.configure(state="disabled", text="Grabbing...")
        def _work():
            from site_grabber import grab
            from config import config
            downloadable, internal = grab(url, user_agent=config.get("user_agent", ""))
            self.results = downloadable
            self.after(0, lambda: self._on_done(downloadable, internal))
        threading.Thread(target=_work, daemon=True).start()

    def _on_done(self, downloadable, internal):
        self.btn.configure(state="normal", text="Grab")
        self.listbox.configure(state="normal")
        self.listbox.delete("1.0", "end")
        self.listbox.insert("end", f"Found {len(downloadable)} downloadable files:\n\n")
        for i, d in enumerate(downloadable):
            self.listbox.insert("end", f"[{i:3d}] {d['filename']}  ({d['ext']})\n     {d['url']}\n")
        self.listbox.insert("end", f"\nAlso found {len(internal)} internal links (not shown).\n")
        self.listbox.configure(state="disabled")
        if downloadable:
            self.dl_btn.configure(state="normal")

    def _download(self):
        idx_str = ctk.CTkInputDialog(text="Enter file # from the list above:",
                                     title="File", default="0").get_input()
        if idx_str is None:
            return
        try:
            idx = int(idx_str)
            item = self.results[idx]
        except (ValueError, IndexError):
            messagebox.showerror("Invalid", "Please enter a valid number.", parent=self)
            return
        self.on_download(item["url"], item["filename"], True, "Auto-detect", "")
        messagebox.showinfo("Added", f"Added: {item['filename']}", parent=self)
