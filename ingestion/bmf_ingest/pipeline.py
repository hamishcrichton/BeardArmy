from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

from loguru import logger

from .config import Settings
from .models import Video, Restaurant, Challenge
from .youtube_client import list_videos, fetch_videos, probe_captions_available, download_captions
from .extractors import extract_from_video
from .geocode import geocode
from .featured_places import get_featured_place
from .repository import DbRepository
from .publish import publish_artifacts, write_json
from sqlalchemy import text


class Pipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.repo = DbRepository(settings.database_url) if settings.database_url else None

    def backfill(self, channel_id: str) -> None:
        vids = list(list_videos(self.settings.youtube_api_key, channel_id))
        self._process_videos(vids)

    def refresh(self, channel_id: str, since_days: int = 7) -> None:
        # Use timezone-aware UTC to compare with API timestamps
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        vids = list(list_videos(self.settings.youtube_api_key, channel_id, published_after=cutoff))
        self._process_videos(vids)

    def _process_videos(self, video_ids: List[str]):
        if not video_ids:
            logger.info("No videos to process.")
            return
        videos = fetch_videos(self.settings.youtube_api_key, video_ids)
        for v in videos:
            try:
                v.captions_available = probe_captions_available(v.video_id)
                captions_path = download_captions(v.video_id, os.path.join(self.settings.data_dir, "captions")) if v.captions_available else None
                if self.repo:
                    self.repo.upsert_video(v)

                ext = extract_from_video(v)

                # Prefer YouTube "Featured places" when available; then heuristics; then city-level fallback.
                restaurant_id = None
                featured = None
                try:
                    featured = get_featured_place(v.video_id)
                except Exception as e:
                    logger.warning(f"Featured place scrape failed for {v.video_id}: {e}")

                if featured:
                    fp_name, fp_lat, fp_lng = featured
                    rest = Restaurant(
                        id=None,
                        name=fp_name,
                        address=None,
                        city=ext.city,
                        region=None,
                        country_code=ext.country,
                        lat=fp_lat,
                        lng=fp_lng,
                        place_source="youtube_featured",
                        place_ref=v.video_id,
                    )
                    if (fp_lat is None or fp_lng is None) and self.settings.geocoder_api_key:
                        # try to geocode the featured name with hints to get coordinates
                        q = " ".join([s for s in [fp_name, ext.city, ext.country] if s])
                        g = geocode(self.settings.geocoder_provider, self.settings.geocoder_api_key, q)
                        rest.address = g.address
                        rest.city = g.city or rest.city
                        rest.region = g.region or rest.region
                        rest.country_code = g.country_code or rest.country_code
                        rest.lat = g.lat or rest.lat
                        rest.lng = g.lng or rest.lng
                        rest.place_source = g.place_source or rest.place_source
                        rest.place_ref = g.place_ref or rest.place_ref
                    if self.repo:
                        restaurant_id = self.repo.upsert_restaurant(rest)
                elif ext.restaurant_name:
                    q = f"{ext.restaurant_name} {ext.city or ''} {ext.country or ''}".strip()
                    logger.info(f"Geocoding restaurant candidate for {v.video_id}: {q}")
                    geo = geocode(self.settings.geocoder_provider, self.settings.geocoder_api_key, q)
                    rest = Restaurant(
                        id=None,
                        name=ext.restaurant_name,
                        address=geo.address,
                        city=geo.city or ext.city,
                        region=geo.region,
                        country_code=geo.country_code,
                        lat=geo.lat,
                        lng=geo.lng,
                        place_source=geo.place_source,
                        place_ref=geo.place_ref,
                    )
                    if self.repo:
                        restaurant_id = self.repo.upsert_restaurant(rest)
                elif ext.city or ext.country:
                    q = \
                        ", ".join([p for p in [ext.city, ext.country] if p])
                    logger.info(f"Geocoding approximate city centroid for {v.video_id}: {q}")
                    geo = geocode(self.settings.geocoder_provider, self.settings.geocoder_api_key, q)
                    if geo.lat is not None and geo.lng is not None:
                        approx_name = (ext.city or ext.country or "Unknown") + " (approx)"
                        rest = Restaurant(
                            id=None,
                            name=approx_name,
                            address=geo.address,
                            city=geo.city or ext.city,
                            region=geo.region,
                            country_code=geo.country_code or (ext.country if ext.country else None),
                            lat=geo.lat,
                            lng=geo.lng,
                            place_source="approx",
                            place_ref=q,
                        )
                        if self.repo:
                            restaurant_id = self.repo.upsert_restaurant(rest)
                    else:
                        logger.info(f"No geocode result for approximate query: {q}")
                
                challenge = Challenge(
                    id=None,
                    video_id=v.video_id,
                    restaurant_id=restaurant_id,
                    date_attempted=ext.date_attempted,
                    result=ext.result,
                    challenge_type_slug=ext.challenge_type_slug,
                    notes=None,
                    charity_flag=False,
                    source="auto",
                    confidence=ext.confidence,
                )
                if self.repo:
                    self.repo.insert_challenge(challenge)
            except Exception as e:
                logger.exception(f"Failed processing video {v.video_id}: {e}")

    def publish(self, out_dir: str) -> None:
        # Basic publish: write an index and, if DB is configured, a GeoJSON of challenges and a table JSON
        datasets: Dict[str, Dict] = {
            "index": {"version": 1, "generated_at": datetime.utcnow().isoformat()},
        }
        publish_artifacts(out_dir, datasets)

        if not self.repo:
            logger.info("No DATABASE_URL configured; skipping DB-backed artifacts.")
            return

        base_sql = (
            """
            SELECT c.id AS challenge_id,
                   c.video_id,
                   v.title,
                   r.name AS restaurant,
                   r.address,
                   r.city,
                   r.country_code,
                   r.lat,
                   r.lng,
                   r.place_source,
                   c.date_attempted,
                   c.result,
                   ct.slug AS type,
                   v.thumbnail_url
            FROM challenges c
            LEFT JOIN restaurants r ON r.id = c.restaurant_id
            LEFT JOIN videos v ON v.video_id = c.video_id
            LEFT JOIN challenge_types ct ON ct.id = c.challenge_type_id
            ORDER BY COALESCE(c.date_attempted, v.published_at) DESC
            """
        )
        limit = os.getenv("PUBLISH_LIMIT")
        if limit and str(limit).strip():
            q = text(base_sql + "\nLIMIT :limit")
            params = {"limit": int(limit)}
        else:
            q = text(base_sql)
            params = {}

        features = []
        rows = []
        with self.repo.engine.connect() as conn:
            res = conn.execute(q, params)
            for r in res.mappings():
                # Normalize date_attempted to ISO string regardless of backend
                da = r["date_attempted"]
                if hasattr(da, "isoformat"):
                    da_iso = da.isoformat()
                else:
                    da_iso = str(da) if da is not None else None
                props = {
                    "id": r["challenge_id"],
                    "video_id": r["video_id"],
                    "title": r["title"],
                    "restaurant": r["restaurant"],
                    "address": r["address"],
                    "city": r["city"],
                    "country_code": r["country_code"],
                    "date_attempted": da_iso,
                    "result": r["result"],
                    "type": r["type"],
                    "thumbnail_url": r["thumbnail_url"],
                    # Include minimal provenance so we can distinguish approx points in the UI later
                    # (kept generic to avoid leaking provider details beyond a label)
                    "place_source": r.get("place_source") if hasattr(r, "get") else None,
                }
                if r["lat"] is not None and r["lng"] is not None:
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [float(r["lng"]), float(r["lat"])]},
                        "properties": props,
                    })
                rows.append(props)

        geojson = {"type": "FeatureCollection", "features": features}
        logger.info(f"Publishing artifacts: {len(features)} features, {len(rows)} rows")
        write_json(os.path.join(out_dir, "challenges.geojson"), geojson)
        write_json(os.path.join(out_dir, "table.json"), {"rows": rows})
