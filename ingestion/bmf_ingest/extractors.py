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
    # Include tags in the text to search
    text = f"{video.title}\n{video.description}"
    if video.tags:
        text += "\n" + " ".join(video.tags)
    
    # Check localizations for additional hints
    localized_texts = []
    if video.localizations:
        for lang_code, localized in video.localizations.items():
            if localized.get("title"):
                localized_texts.append(localized["title"])
            if localized.get("description"):
                localized_texts.append(localized["description"][:500])  # First 500 chars

    # Date: if title/description mention an explicit date, prefer it; else use publish date
    explicit_date = _find_date(text)
    date_attempted = explicit_date or video.published_at.date()

    # Restaurant + location hints - search in main text and localizations
    restaurant = _find_restaurant_name(text)
    if not restaurant and localized_texts:
        for lt in localized_texts:
            restaurant = _find_restaurant_name(lt)
            if restaurant:
                break
    
    city, country = _find_city_country(text)
    if not city and not country and localized_texts:
        for lt in localized_texts:
            city_loc, country_loc = _find_city_country(lt)
            if city_loc or country_loc:
                city = city or city_loc
                country = country or country_loc
                break

    # Result
    result, result_conf = _find_result(text)

    # Type
    ctype, type_conf = _find_type(text)

    # Collaborators (simple @ or name patterns; refine later)
    collaborators = _find_collaborators(text)

    # Boost confidence if we have tags or localizations
    has_enhanced_metadata = bool(video.tags) or bool(video.localizations)
    confidence = min(1.0, (0.4 if restaurant else 0.2) + 0.2 + result_conf * 0.2 + type_conf * 0.2 + (0.1 if has_enhanced_metadata else 0))

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


def _clean_restaurant(candidate: str) -> str:
    candidate = candidate.strip().strip("'\"")
    candidate = re.sub(r"^(?:a|the)\s+(?:restaurant|place|spot)\s+called\s+", "", candidate, flags=re.I)
    candidate = re.sub(r"^(?:at|in)\s+", "", candidate, flags=re.I)
    candidate = re.split(r"\s+(?:in|at|near|with|by|from)\b|[\,\.;\n\|\-]", candidate)[0].strip()
    candidate = re.sub(r"\s{2,}", " ", candidate)
    return candidate


def _find_restaurant_name(text: str) -> Optional[str]:
    # First try BMF's common title formats
    lines = text.split('\n')
    if lines:
        title = lines[0]
        
        # Format: "Restaurant Name | City, Country | Challenge Type"
        # or "Restaurant Name | City | Challenge"
        pipe_parts = [p.strip() for p in title.split('|')]
        if len(pipe_parts) >= 2:
            # First part is often the restaurant name
            restaurant = pipe_parts[0].strip()
            # Clean common prefixes/suffixes
            restaurant = re.sub(r'^(The\s+)?', '', restaurant, flags=re.I)
            restaurant = re.sub(r'\s+(Challenge|Eating|Food|Restaurant|Diner|Cafe|Grill|Bar|Pub)$', '', restaurant, flags=re.I)
            if restaurant and 1 <= len(restaurant.split()) <= 8:
                return restaurant
        
        # Format: "Challenge at Restaurant Name in City"
        m = re.match(r'^[^@]+\s+(?:at|@)\s+([^in]+?)\s+in\s+', title, re.I)
        if m:
            cand = _clean_restaurant(m.group(1))
            if cand and 1 <= len(cand.split()) <= 8:
                return cand
    
    # Fallback to original heuristics
    patterns = [
        r"\bat\s+(?:a\s+(?:place|restaurant|spot)\s+called\s+)?['\"]?([A-Z][\w'&\- ]{2,})",
        r"\bcalled\s+['\"]?([A-Z][\w'&\- ]{2,})",
        r"\bat\s+(?:the\s+|a\s+)?(['\"]?[A-Z][\w'&\- ]{2,})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            cand = _clean_restaurant(m.group(1))
            if 1 <= len(cand.split()) <= 8:
                return cand
    return None


def _find_city_country(text: str) -> Tuple[Optional[str], Optional[str]]:
    lines = text.split('\n')
    if lines:
        title = lines[0]
        
        # First check pipe-delimited format
        pipe_parts = [p.strip() for p in title.split('|')]
        if len(pipe_parts) >= 2:
            # Second part is often "City, Country" or "City, State"
            location_part = pipe_parts[1].strip()
            
            # Check for "City, Country" or "City, State" format
            loc_match = re.match(r'^([^,]+)(?:,\s*(.+))?$', location_part)
            if loc_match:
                city = loc_match.group(1).strip()
                region = (loc_match.group(2) or "").strip() if loc_match.group(2) else None
                
                # Check if region is a US state abbreviation
                if region and len(region) == 2 and region.isupper():
                    return (f"{city}, {region}", "US")
                elif region:
                    # Map common country names
                    country_map = {
                        "UK": "UK", "United Kingdom": "UK", "England": "UK", 
                        "Scotland": "UK", "Wales": "UK", "Northern Ireland": "UK",
                        "USA": "US", "United States": "US", "America": "US",
                        "Canada": "CA", "Australia": "AU", "Germany": "DE",
                        "France": "FR", "Spain": "ES", "Italy": "IT", "Japan": "JP"
                    }
                    country = country_map.get(region, region)
                    return (city, country)
                elif city:
                    return (city, None)
    
    # Original pattern matching
    m = re.search(r"\bin\s+([A-Z][A-Za-z'\- ]{1,}?)(?:,\s*([A-Z]{2}))?(?=(?:\s+(?:at|with|near|from|and)\b|[\,\.;:\|]|$))", text)
    if m:
        city = m.group(1).strip()
        state = (m.group(2) or "").strip()
        if state:
            return (f"{city}, {state}", "US")
        return (city, None)
    
    # Fallback: common country mentions
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
