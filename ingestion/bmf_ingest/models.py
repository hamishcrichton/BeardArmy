from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any


@dataclass
class Video:
    video_id: str
    title: str
    description: str
    published_at: datetime
    duration_seconds: Optional[int] = None
    captions_available: bool = False
    playlist_ids: List[str] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    channel_id: Optional[str] = None
    raw_json: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Restaurant:
    id: Optional[int]
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    status: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    place_source: Optional[str] = None
    place_ref: Optional[str] = None
    last_verified_at: Optional[datetime] = None


@dataclass
class Challenge:
    id: Optional[int]
    video_id: str
    restaurant_id: Optional[int]
    date_attempted: Optional[date]
    result: str = "unknown"  # success|failure|unknown
    challenge_type_slug: Optional[str] = None
    time_limit: Optional[timedelta] = None
    price_cents: Optional[int] = None
    notes: Optional[str] = None
    charity_flag: bool = False
    source: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class Collaborator:
    id: Optional[int]
    name: str
    yt_channel_id: Optional[str] = None
    website: Optional[str] = None
    image_url: Optional[str] = None


@dataclass
class Artifact:
    name: str
    content: Dict[str, Any]
    path: str

