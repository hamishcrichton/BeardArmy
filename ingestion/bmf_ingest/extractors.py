from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, Iterable, List, Optional, Tuple

from dateparser import parse as parse_date
from rapidfuzz import fuzz

from .models import Video


_RESULT_PATTERNS = [
    ("success", re.compile(r"\b(completed|did it|won|success)\b", re.I)),
    ("failure", re.compile(r"\b(failed|couldn'?t|loss|dnf)\b", re.I)),
]

_TYPE_PATTERNS = [
    ("quantity", re.compile(r"\b(all-you-can-eat|massive|giant|huge|stack|kilo|challenge)\b", re.I)),
    ("spicy", re.compile(r"\b(spicy|carolina reaper|ghost pepper|hot wing)\b", re.I)),
    ("speed", re.compile(r"\b(speed|fastest|time trial|\d+ ?min(?:ute)?s?)\b", re.I)),
]


@dataclass
class Extracted:
    restaurant_name: Optional[str]
    city: Optional[str]
    country: Optional[str]
    date_attempted: Optional[date]
    collaborators: List[str]
    result: str
    challenge_type_slug: Optional[str]
    confidence: float


def extract_from_video(video: Video) -> Extracted:
    text = f"{video.title}\n{video.description}"

    # Date: if title/description mention an explicit date, prefer it; else use publish date
    explicit_date = _find_date(text)
    date_attempted = explicit_date or video.published_at.date()

    # Restaurant + location hints
    restaurant = _find_restaurant_name(text)
    city, country = _find_city_country(text)

    # Result
    result, result_conf = _find_result(text)

    # Type
    ctype, type_conf = _find_type(text)

    # Collaborators (simple @ or name patterns; refine later)
    collaborators = _find_collaborators(text)

    confidence = min(1.0, (0.4 if restaurant else 0.2) + 0.2 + result_conf * 0.2 + type_conf * 0.2)

    return Extracted(
        restaurant_name=restaurant,
        city=city,
        country=country,
        date_attempted=date_attempted,
        collaborators=collaborators,
        result=result,
        challenge_type_slug=ctype,
        confidence=confidence,
    )


def _find_date(text: str) -> Optional[date]:
    # Look for patterns like 12 Jan 2024, Jan 12, 2024, 2024-01-12
    m = re.search(r"(\b\d{1,2}\s+\w+\s+\d{4}\b|\b\w+\s+\d{1,2},\s*\d{4}\b|\b\d{4}-\d{2}-\d{2}\b)", text)
    if m:
        dt = parse_date(m.group(0))
        if dt:
            return dt.date()
    return None


def _find_restaurant_name(text: str) -> Optional[str]:
    # Heuristics focusing on "at ..." (avoid treating "in City" as a restaurant).
    patterns = [
        # at a place called Mama Bear's Diner
        r"\bat\s+(?:a\s+place\s+called\s+)?['\"]?([A-Z][\w'&\- ]{2,})",
        # at The Big Burger House
        r"\bat\s+(?:the\s+|a\s+)?(['\"]?[A-Z][\w'&\- ]{2,})",
        # called Mama Bear's Diner
        r"\bcalled\s+['\"]?([A-Z][\w'&\- ]{2,})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            candidate = m.group(1).strip().strip('"\'')
            # Trim trailing punctuation and overly long tails
            candidate = re.split(r"[\,\.;\n]", candidate)[0].strip()
            if 1 <= len(candidate.split()) <= 8:
                return candidate
    return None


def _find_city_country(text: str) -> Tuple[Optional[str], Optional[str]]:
    # Capture patterns like "in Schuylerville, NY" → ("Schuylerville NY", "US")
    m = re.search(r"\bin\s+([A-Z][A-Za-z'\- ]{2,})(?:,\s*([A-Z]{2}))?", text)
    if m:
        city = m.group(1).strip()
        state = (m.group(2) or "").strip()
        if state:
            return (f"{city} {state}", "US")
        return (city, None)
    # Fallback: common country mentions (very rough)
    countries = [
        "USA","United States","US","UK","United Kingdom","England","Scotland","Wales","Ireland",
        "Canada","Australia","New Zealand","Germany","France","Spain","Italy","Japan","Mexico","New York"
    ]
    for c in countries:
        if re.search(rf"\b{re.escape(c)}\b", text, re.I):
            if c in {"UK","United Kingdom","England","Scotland","Wales"}:
                return (None, "UK")
            if c in {"USA","United States","US","New York"}:
                return (None, "US")
            return (None, c)
    return (None, None)


def _find_result(text: str) -> Tuple[str, float]:
    for label, pat in _RESULT_PATTERNS:
        if pat.search(text):
            return label, 1.0
    return "unknown", 0.2


def _find_type(text: str) -> Tuple[Optional[str], float]:
    for slug, pat in _TYPE_PATTERNS:
        if pat.search(text):
            return slug, 0.8
    return None, 0.2


def _find_collaborators(text: str) -> List[str]:
    # Collect @handles and Title Case names after "with"
    handles = re.findall(r"@([A-Za-z0-9_\.]+)", text)
    collab_match = re.search(r"\bwith\s+([A-Z][\w\s&]{2,40})", text)
    names = [collab_match.group(1).strip()] if collab_match else []
    return list(dict.fromkeys([*handles, *names]))
