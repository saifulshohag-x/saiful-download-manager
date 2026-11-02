"""
speed_graph.py - IDM-style real-time speed graph widget.

A lightweight pure-Tkinter Canvas widget that draws a scrolling line graph of
total download speed over the last ~60 seconds. No matplotlib needed - keeps
the .exe small.
"""
import time
import customtkinter as ctk


class SpeedGraph(ctk.CTkFrame):
    """Scrolling speed graph showing total KB/s over time."""

    def __init__(self, master, width=260, height=80, max_points=120):
        super().__init__(master, fg_color="#111111", corner_radius=4)
        self.width = width
        self.height = height
        self.max_points = max_points
        self.points = []  # list of (timestamp, kbps)
        self._max_seen = 100.0  # auto-scaling max KB/s
        self.label = ctk.CTkLabel(self, text="Speed graph", anchor="w",
                                  font=ctk.CTkFont(size=10),
                                  text_color="#888")
        self.label.pack(padx=4, pady=(2, 0), anchor="w")
        self.canvas = ctk.CTkCanvas(self, width=width, height=height,
                                    bg="#111111", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)

    def add_point(self, kbps: float):
        now = time.time()
        self.points.append((now, kbps))
        # Trim to max_points
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]
        # Auto-scale max
        cur_max = max((p[1] for p in self.points), default=10.0)
        if cur_max > self._max_seen:
            self._max_seen = cur_max * 1.1
        elif cur_max < self._max_seen * 0.5 and self._max_seen > 100:
            self._max_seen = max(100.0, cur_max * 1.1)
        self._redraw()

    def _redraw(self):
        w = int(self.canvas.winfo_width() or self.width)
        h = int(self.canvas.winfo_height() or self.height)
        self.canvas.delete("all")
        if not self.points or w < 10 or h < 10:
            return
        # Grid lines
        for i in range(1, 4):
            y = h * i // 4
            self.canvas.create_line(0, y, w, y, fill="#222", dash=(2, 2))
        # Plot points
        n = len(self.points)
        if n < 2:
            return
        # x spacing: spread points across full width
        step_x = w / max(1, (self.max_points - 1))
        max_v = self._max_seen
        coords = []
        for i, (t, v) in enumerate(self.points):
            x = w - (n - 1 - i) * step_x
            if x < 0:
                x = 0
            y = h - (v / max_v * h * 0.9) if max_v > 0 else h
            coords.append((x, y))
        # Fill area under curve
        if len(coords) >= 2:
            poly = [coords[0][0], h]
            for x, y in coords:
                poly.append(x)
                poly.append(y)
            poly.append(coords[-1][0])
            poly.append(h)
            self.canvas.create_polygon(poly, outline="", fill="#0d3d1f")
            # Line on top
            line = []
            for x, y in coords:
                line.append(x)
                line.append(y)
            self.canvas.create_line(line, fill="#1aa260", width=2, smooth=True)
        # Current value label (top-right)
        cur_kbps = self.points[-1][1]
        if cur_kbps >= 1024:
            val = f"{cur_kbps/1024:.2f} MB/s"
        else:
            val = f"{cur_kbps:.1f} KB/s"
        self.canvas.create_text(w - 6, 8, text=val, anchor="ne",
                                fill="#1aa260", font=("Consolas", 9, "bold"))

    def reset(self):
        self.points = []
        self._max_seen = 100.0
        self.canvas.delete("all")
