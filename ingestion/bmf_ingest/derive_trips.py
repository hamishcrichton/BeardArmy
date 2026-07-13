"""Derive trip/series names for challenges, deterministically (no LLM).

Two signals, applied in priority order per video:
1. Named series in the title — "The Trip To Miami Pt.3", "NYC Mini-Series Pt.1",
   "Texas Road Trip" etc. The series phrase is normalized and reused across its
   episodes.
2. Date-contiguous runs of consecutive away-from-home (non-GB) challenges with
   gaps of <= 21 days collapse into one trip, named "<Country/Region> trip,
   <Month Year>" (e.g. "US trip, May 2019").

Returns {video_id: trip_name}; videos at home with no named series get None.
Used by Pipeline.publish via derive_trip_names().
"""
from __future__ import annotations

import re
from datetime import date, datetime

HOME = "GB"
MAX_GAP_DAYS = 21
MIN_TRIP_SIZE = 2

_SERIES_PATTERNS = [
    # "THE TRIP TO MIAMI PT.3", "The Trip To Vegas Part 2"
    re.compile(r"the trip to ([a-z' ]+?)\s*(?:pt|part|ep)\.?\s*\d", re.I),
    # "NYC MINI-SERIES PT.1", "TEXAS MINI SERIES EP 2"
    re.compile(r"([a-z' ]+?)\s*mini[- ]?series", re.I),
    # "TEXAS ROAD TRIP", "WEST COAST TOUR"
    re.compile(r"([a-z' ]+?)\s*(?:road ?trip|tour)\b", re.I),
]

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

COUNTRY_NAMES = {
    "US": "USA", "IE": "Ireland", "DE": "Germany", "NL": "Netherlands", "BE": "Belgium",
    "FR": "France", "ES": "Spain", "IT": "Italy", "AT": "Austria", "CZ": "Czechia",
    "PL": "Poland", "SE": "Sweden", "NO": "Norway", "DK": "Denmark", "FI": "Finland",
    "CA": "Canada", "AU": "Australia", "NZ": "New Zealand", "AE": "UAE", "SG": "Singapore",
    "TH": "Thailand", "JP": "Japan", "MX": "Mexico", "CH": "Switzerland", "PT": "Portugal",
}


def _series_from_title(title: str) -> str | None:
    for pat in _SERIES_PATTERNS:
        m = pat.search(title or "")
        if m:
            name = re.sub(r"\s+", " ", m.group(1)).strip(" '").title()
            # discard generic/degenerate captures ("The", "A", one letter)
            if len(name) >= 3 and name.lower() not in {"the", "food", "eating"}:
                return name
    return None


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def derive_trip_names(rows: list[dict]) -> dict[str, str]:
    """rows: [{video_id, title, country_code, date_attempted}] -> {video_id: trip_name}."""
    out: dict[str, str] = {}

    # 1. named series from titles
    series_members: dict[str, list[str]] = {}
    for r in rows:
        s = _series_from_title(r.get("title") or "")
        if s:
            series_members.setdefault(s, []).append(r["video_id"])
    for name, vids in series_members.items():
        for v in vids:
            out[v] = name

    # 2. contiguous away runs (date order), for videos not already in a named series
    dated = sorted(
        (r for r in rows if _parse_date(r.get("date_attempted"))),
        key=lambda r: _parse_date(r["date_attempted"]),
    )
    run: list[dict] = []

    def flush(run: list[dict]) -> None:
        if len(run) < MIN_TRIP_SIZE:
            return
        ccs = [r.get("country_code") for r in run if r.get("country_code")]
        main_cc = max(set(ccs), key=ccs.count) if ccs else None
        where = COUNTRY_NAMES.get(main_cc, main_cc or "Away")
        d0 = _parse_date(run[0]["date_attempted"])
        name = f"{where} trip, {_MONTHS[d0.month - 1]} {d0.year}"
        for r in run:
            out.setdefault(r["video_id"], name)

    prev_date: date | None = None
    for r in dated:
        cc, d = r.get("country_code"), _parse_date(r["date_attempted"])
        away = cc is not None and cc != HOME
        if away and (not run or (prev_date and (d - prev_date).days <= MAX_GAP_DAYS)):
            run.append(r)
        elif away:
            flush(run)
            run = [r]
        else:
            flush(run)
            run = []
        prev_date = d if away else prev_date
    flush(run)

    return out
