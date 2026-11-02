"""
batch_download.py - IDM-style batch download with URL patterns.

Expands a URL template like:
    https://example.com/file[01-10].zip
into 10 URLs:
    https://example.com/file01.zip
    https://example.com/file02.zip
    ...
    https://example.com/file10.zip

Supports zero-padded ranges [001-100] and multiple ranges in the same URL.
"""
import re
from typing import List

RANGE_RE = re.compile(r"\[(\d+)-(\d+)\]")


def expand_pattern(pattern: str) -> List[str]:
    """Expand a URL pattern with [start-end] ranges into a list of URLs."""
    matches = list(RANGE_RE.finditer(pattern))
    if not matches:
        return [pattern]
    # Build the cartesian product of all ranges
    ranges = []
    for m in matches:
        start = int(m.group(1))
        end = int(m.group(2))
        if start > end:
            start, end = end, start
        # width based on the original string (zero-padded if start had leading zeros)
        width = len(m.group(1))
        ranges.append((start, end, width))
    urls = []
    _expand_recursive(pattern, 0, ranges, 0, {}, urls)
    return urls


def _expand_recursive(pattern, range_idx, ranges, _depth, current_values, urls):
    if range_idx >= len(ranges):
        # Substitute all ranges
        result = pattern
        i = 0
        for m in RANGE_RE.finditer(pattern):
            v = current_values[i]
            start, end, width = ranges[i]
            replacement = str(v).zfill(width)
            result = result.replace(m.group(0), replacement, 1)
            i += 1
        urls.append(result)
        return
    start, end, width = ranges[range_idx]
    for v in range(start, end + 1):
        current_values[range_idx] = v
        _expand_recursive(pattern, range_idx + 1, ranges, _depth + 1, current_values, urls)
