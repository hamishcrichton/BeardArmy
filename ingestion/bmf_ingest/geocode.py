from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class GeoResult:
    lat: Optional[float]
    lng: Optional[float]
    address: Optional[str]
    city: Optional[str]
    region: Optional[str]
    country_code: Optional[str]
    place_source: Optional[str]
    place_ref: Optional[str]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
def geocode_opencage(q: str, api_key: str) -> GeoResult:
    url = "https://api.opencagedata.com/geocode/v1/json"
    r = requests.get(url, params={"q": q, "key": api_key, "limit": 1, "abbrv": 1})
    r.raise_for_status()
    js = r.json()
    if not js.get("results"):
        return GeoResult(None, None, None, None, None, None, "opencage", None)
    res = js["results"][0]
    comp = res.get("components", {})
    return GeoResult(
        lat=res["geometry"]["lat"],
        lng=res["geometry"]["lng"],
        address=res.get("formatted"),
        city=comp.get("city") or comp.get("town") or comp.get("village"),
        region=comp.get("state"),
        country_code=comp.get("country_code", "").upper() or None,
        place_source="opencage",
        place_ref=res.get("annotations", {}).get("what3words", {}).get("words"),
    )


def geocode(provider: str | None, api_key: str | None, query: str) -> GeoResult:
    if provider == "opencage" and api_key:
        try:
            return geocode_opencage(query, api_key)
        except Exception as e:
            logger.warning(f"OpenCage geocode failed: {e}")
    # Fallback empty
    return GeoResult(None, None, None, None, None, None, provider, None)

