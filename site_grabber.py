"""
site_grabber.py - Light-weight website spider / link extractor.

Like IDM's Grabber: given a URL, downloads the page and lists every
downloadable link (file extensions like .zip, .pdf, .mp4) and every
internal link, so the user can pick which to download.
"""
import re
import os
from urllib.parse import urljoin, urlparse, unquote
from typing import List, Tuple
import requests

from clipboard_monitor import DOWNLOAD_EXTS


A_HREF_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.IGNORECASE)
SRC_RE = re.compile(r'<(?:img|video|audio|source|embed)[^>]+src=["\']([^"\']+)["\']',
                    re.IGNORECASE)


def grab(url: str, timeout: int = 30, user_agent: str = "") -> Tuple[List[dict], List[str]]:
    """Download a page and return (downloadable_files, internal_links).

    Each entry in downloadable_files is:
        {"url": ..., "filename": ..., "ext": ..., "size_hint": 0}
    """
    headers = {"User-Agent": user_agent or "Mozilla/5.0",
               "Accept-Encoding": "identity"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        return ([], [f"Error fetching page: {e}"])

    base = url
    downloadable = []
    internal = set()
    seen = set()

    for m in A_HREF_RE.findall(html) + SRC_RE.findall(html):
        if not m or m.startswith(("javascript:", "mailto:", "#", "data:")):
            continue
        full = urljoin(base, m)
        try:
            parsed = urlparse(full)
        except Exception:
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        if full in seen:
            continue
        seen.add(full)
        path = unquote(parsed.path).lower()
        _, ext = os.path.splitext(path)
        if ext in DOWNLOAD_EXTS:
            filename = unquote(os.path.basename(parsed.path)) or "download" + ext
            downloadable.append({
                "url": full,
                "filename": filename,
                "ext": ext,
                "size_hint": 0,
            })
        else:
            # internal page link (same host)
            if parsed.netloc == urlparse(base).netloc:
                internal.add(full)

    return (downloadable, sorted(internal))
