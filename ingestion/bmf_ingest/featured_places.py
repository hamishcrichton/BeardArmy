from __future__ import annotations

import re
from typing import Optional, Tuple

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


_GOOGLE_MAPS_RE = re.compile(r'https?://www\.google\.(?:com|[a-z]{2})(?:\.[a-z]{2})?/maps/[^"]+', re.I)
_COORD_RE = re.compile(r"/@(?P<lat>-?\d+\.\d+),(?P<lng>-?\d+\.\d+),")
_ANCHOR_RE = re.compile(r"<a[^>]+href=\"(?P<href>[^\"]+)\"[^>]*>(?P<text>[^<]+)</a>", re.I)


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

    # Look for anchor tags that link to Google Maps; pick the first as the primary featured place.
    anchors = list(_ANCHOR_RE.finditer(html))
    for a in anchors:
        href = a.group("href")
        if not _GOOGLE_MAPS_RE.search(href):
            continue
        text = a.group("text").strip()
        # Extract coordinates if present in URL path
        m = _COORD_RE.search(href)
        lat = float(m.group("lat")) if m else None
        lng = float(m.group("lng")) if m else None
        # Clean obvious unhelpful texts
        if text and len(text) > 1 and text.lower() not in {"google maps", "maps"}:
            logger.info(f"Found featured place for {video_id}: {text} ({lat},{lng})")
            return text, lat, lng

    logger.info(f"No featured place anchors found for {video_id}")
    return None
