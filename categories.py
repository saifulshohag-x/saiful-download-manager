"""
categories.py - IDM-style file categories.

Each download is auto-categorized by file extension. IDM has these default
categories:
  - Compressed: zip, rar, 7z, tar, gz
  - Documents:  pdf, doc, docx, txt, rtf, xls, xlsx, ppt, pptx
  - Music:      mp3, wav, flac, aac, ogg, m4a
  - Programs:   exe, msi, bat, cmd, com
  - Video:      mp4, avi, mkv, mov, wmv, flv, webm, mpg, mpeg
  - Images:     jpg, jpeg, png, gif, bmp, webp, svg

Files are saved into subfolders named after the category (when
category_folders=True). Uncategorized files go to the root download folder.
"""
import os
from typing import Optional


CATEGORIES = [
    # (id, display_name, icon, extensions[], color)
    ("compressed", "Compressed", "📦", [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"], "#c08430"),
    ("documents",  "Documents",  "📄", [".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx",
                                       ".ppt", ".pptx", ".odt", ".ods", ".odp", ".csv"], "#3a7fc4"),
    ("music",      "Music",      "🎵", [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
                                       ".wma", ".opus"], "#9b3ec4"),
    ("programs",   "Programs",   "⚙️", [".exe", ".msi", ".bat", ".cmd", ".com", ".ps1",
                                       ".apk", ".dmg", ".deb", ".rpm"], "#c43e3e"),
    ("video",      "Video",      "🎬", [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
                                       ".webm", ".mpg", ".mpeg", ".m4v", ".3gp"], "#c43e8a"),
    ("images",     "Images",     "🖼️", [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
                                       ".svg", ".tiff", ".ico", ".psd"], "#3ec46a"),
]

# Virtual categories that don't depend on file extension
VIRTUAL_CATEGORIES = [
    # (id, display_name, icon, color)
    ("all",         "All Downloads", "📥", "#1aa260"),
    ("unfinished",  "Unfinished",    "⏳", "#c4a23e"),
    ("finished",    "Finished",      "✅", "#3ec46a"),
    ("grabber",     "Grabber",       "🕸️", "#3a4a8a"),
    ("dropbox",     "Drop Box",      "🎯", "#777777"),
]


def get_category_id(filename: str) -> str:
    """Return the category id for a filename based on its extension."""
    ext = os.path.splitext(filename)[1].lower()
    for cid, _, _, exts, _ in CATEGORIES:
        if ext in exts:
            return cid
    return "other"


def get_category_info(category_id: str):
    """Return (display_name, icon, color) for a category id."""
    for cid, name, icon, _, color in CATEGORIES:
        if cid == category_id:
            return (name, icon, color)
    for cid, name, icon, color in VIRTUAL_CATEGORIES:
        if cid == category_id:
            return (name, icon, color)
    return ("Other", "📁", "#777777")


def get_target_folder(base_folder: str, filename: str, use_subfolders: bool = True) -> str:
    """Return the destination folder for a file, possibly with a category subfolder."""
    if not use_subfolders:
        return base_folder
    cat_id = get_category_id(filename)
    if cat_id == "other":
        return base_folder
    cat_name = get_category_info(cat_id)[0]
    sub = os.path.join(base_folder, cat_name)
    try:
        os.makedirs(sub, exist_ok=True)
    except Exception:
        return base_folder
    return sub


def get_file_icon(filename: str) -> str:
    """Return an emoji icon for the file based on its type."""
    cat_id = get_category_id(filename)
    return get_category_info(cat_id)[1]
