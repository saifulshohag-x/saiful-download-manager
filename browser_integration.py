"""
browser_integration.py - Local HTTP server that receives URLs from the browser
extension (Chrome / Edge / Firefox) and adds them to the download queue.

The extension POSTs JSON: {"url": "...", "filename": "...", "referer": "..."}
to http://127.0.0.1:9527/add and this server hands it to QueueManager.

A matching Chrome/Edge extension (manifest v3) is provided in
extension/idm_clone_ext/ inside the project. Load it as an unpacked extension.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


class _Handler(BaseHTTPRequestHandler):
    """HTTP request handler for the integration endpoint."""

    # Silence default logging
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, {"ok": True})

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/ping":
            self._send(200, {"ok": True, "service": "Saiful Download Manager"})
        elif path == "/list":
            tasks = []
            if self.server.queue_manager:
                for t in self.server.queue_manager.get_all():
                    tasks.append(t.to_dict())
            self._send(200, {"tasks": tasks})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0) or 0)
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            data = {}
        if path == "/add":
            url = data.get("url", "").strip()
            filename = data.get("filename", "").strip()
            if not url:
                self._send(400, {"error": "missing url"})
                return
            if not self.server.queue_manager:
                self._send(500, {"error": "queue not ready"})
                return
            task = self.server.queue_manager.add(url, filename, auto_start=True)
            self._send(200, {"ok": True, "file_name": task.file_name})
        elif path == "/pause_all":
            if self.server.queue_manager:
                self.server.queue_manager.pause_all()
            self._send(200, {"ok": True})
        elif path == "/start_all":
            if self.server.queue_manager:
                self.server.queue_manager.start_all()
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})


class BrowserIntegrationServer:
    """Wraps the HTTPServer with start/stop helpers."""

    def __init__(self, queue_manager, port: int = 9527):
        self.queue_manager = queue_manager
        self.port = port
        self._httpd = None
        self._thread = None

    def start(self):
        if self._httpd:
            return
        try:
            self._httpd = HTTPServer(("127.0.0.1", self.port), _Handler)
            self._httpd.queue_manager = self.queue_manager
            self._thread = threading.Thread(target=self._httpd.serve_forever,
                                            daemon=True, name="browser-server")
            self._thread.start()
            print(f"[Saiful DM] listening on 127.0.0.1:{self.port}")
        except OSError as e:
            print(f"[BrowserIntegration] failed to bind port {self.port}: {e}")
            self._httpd = None

    def stop(self):
        if self._httpd:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None
            self._thread = None
