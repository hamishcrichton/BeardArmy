from __future__ import annotations

import re
from typing import Optional, Tuple

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


_GOOGLE_MAPS_RE = re.compile(
    r"https?://(?:(?:www\.)?google\.[^/]+/maps|maps\.app\.goo\.gl|goo\.gl/maps|g\.page)/[^'\"<>\s]+",
    re.I,
)
_COORD_RE = re.compile(r"/@(?P<lat>-?\d+\.\d+),(?P<lng>-?\d+\.\d+),")
_ANCHOR_RE = re.compile(r"<a[^>]+href=\"(?P<href>[^\"]+)\"[^>]*>(?P<text>[^<]+)</a>", re.I)
_URL_RE = re.compile(r"https?://[^'\"<>\s]+", re.I)


def _first(seq):
    for x in seq:
        return x
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def get_featured_place(video_id: str) -> Optional[Tuple[str, Optional[float], Optional[float]]]:
    """
    Try to extract a 'Featured places' entry from the YouTube watch page.
    Returns (name, lat, lng) where lat/lng may be None if the link lacks coordinates.
    """
    url = f"https://www.youtube.com/watch?v={video_id}&hl=en&bpctr=9999999999&has_verified=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    html = r.text

    # First pass: explicit anchors with text
    anchors = list(_ANCHOR_RE.finditer(html))
    for a in anchors:
        href = a.group("href")
        if not _GOOGLE_MAPS_RE.search(href):
            continue
        text = a.group("text").strip()
        m = _COORD_RE.search(href)
        lat = float(m.group("lat")) if m else None
        lng = float(m.group("lng")) if m else None
        if text and len(text) > 1 and text.lower() not in {"google maps", "maps"}:
            logger.info(f"Found featured place for {video_id}: {text} ({lat},{lng})")
            return text, lat, lng

    # Second pass: any Maps-like URL anywhere in the HTML (YouTube often renders via JSON without anchors)
    for m in _URL_RE.finditer(html):
        url = m.group(0)
        if not _GOOGLE_MAPS_RE.search(url):
            continue
        # Extract coordinates if present
        mcoord = _COORD_RE.search(url)
        lat = float(mcoord.group("lat")) if mcoord else None
        lng = float(mcoord.group("lng")) if mcoord else None
        # Try to infer a name from the URL path if possible
        name = None
        try:
            from urllib.parse import unquote, urlparse
            path = urlparse(url).path
            # /maps/place/<name>/@... or /maps/place/<name>
            parts = [p for p in path.split('/') if p]
            if 'place' in parts:
                idx = parts.index('place')
                if idx + 1 < len(parts):
                    name = unquote(parts[idx + 1]).replace('+', ' ').strip()
        except Exception:
            pass
        if name:
            logger.info(f"Found featured-like maps URL for {video_id}: {name} ({lat},{lng})")
            return name, lat, lng

    logger.info(f"No featured place anchors found for {video_id}")
    return None
