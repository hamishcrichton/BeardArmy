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

                # Priority order for location data:
                # 1. YouTube recordingDetails (if available)
                # 2. YouTube "Featured places" 
                # 3. Extraction heuristics
                # 4. City-level fallback
                restaurant_id = None
                featured = None
                
                # Check if we have recording location from YouTube API
                has_recording_location = False
                if v.recording_location and v.recording_location.get("lat") and v.recording_location.get("lng"):
                    has_recording_location = True
                    logger.info(f"Found recording location for {v.video_id}: {v.recording_location}")
                
                # Try to get featured place (but skip if we already have recording location)
                if not has_recording_location:
                    try:
                        featured = get_featured_place(v.video_id)
                    except Exception as e:
                        logger.warning(f"Featured place scrape failed for {v.video_id}: {e}")

                if has_recording_location:
                    # Use recording location from YouTube API
                    rest = Restaurant(
                        id=None,
                        name=ext.restaurant_name or v.recording_location.get("description") or f"{ext.city or 'Unknown'} (Recording Location)",
                        address=v.recording_location.get("description"),
                        city=ext.city,
                        region=None,
                        country_code=ext.country,
                        lat=v.recording_location["lat"],
                        lng=v.recording_location["lng"],
                        place_source="youtube_recording",
                        place_ref=v.video_id,
                    )
                    if self.repo:
                        restaurant_id = self.repo.upsert_restaurant(rest)
                elif featured:
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
                    existing_id = self.repo.get_challenge_id_by_video(v.video_id)
                    if existing_id is None:
                        self.repo.insert_challenge(challenge)
                    else:
                        logger.debug(f"Challenge already exists for {v.video_id} (id={existing_id}); skipping insert")
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

    def prototype(
        self,
        channel_id: str,
        limit: int = 25,
        out_dir: str = "public/data",
        use_captions: bool = False,
        use_geocode: bool = False,
    ) -> None:
        """
        Prototype extraction without requiring a DB. Fetch up to `limit` videos,
        run extractors + optional captions/geocode, and emit artifacts for preview.
        """
        vids = []
        all_ids = []
        for i, vid in enumerate(list_videos(self.settings.youtube_api_key, channel_id)):
            all_ids.append(vid)
            if i + 1 >= max(1, limit):
                break
        if not all_ids:
            logger.info("No videos found for prototype.")
            return
        videos = fetch_videos(self.settings.youtube_api_key, all_ids)

        proto_rows = []
        features = []
        details = []

        for v in videos:
            # Optionally probe and download captions (path kept for future NLP enrichment)
            captions_path = None
            if use_captions:
                try:
                    v.captions_available = probe_captions_available(v.video_id)
                    if v.captions_available:
                        captions_path = download_captions(
                            v.video_id,
                            os.path.join(self.settings.data_dir, "captions"),
                        )
                except Exception as e:
                    logger.warning(f"Captions step failed for {v.video_id}: {e}")

            ext = extract_from_video(v)

            rest_name = None
            lat = lng = None
            place_source = None
            address = city = country_code = None

            featured = None
            try:
                featured = get_featured_place(v.video_id)
            except Exception as e:
                logger.warning(f"Featured place scrape failed for {v.video_id}: {e}")

            if featured:
                rest_name, lat, lng = featured[0], featured[1], featured[2]
                place_source = "youtube_featured"
            elif ext.restaurant_name:
                rest_name = ext.restaurant_name

            # Optional geocode: try to improve coords when we have a name or city hints
            if use_geocode and (rest_name or ext.city or ext.country):
                q = " ".join([s for s in [rest_name, ext.city, ext.country] if s])
                try:
                    g = geocode(self.settings.geocoder_provider, self.settings.geocoder_api_key, q)
                    address = g.address or address
                    city = g.city or ext.city or city
                    country_code = g.country_code or country_code
                    lat = g.lat if g.lat is not None else lat
                    lng = g.lng if g.lng is not None else lng
                    place_source = g.place_source or place_source
                except Exception as e:
                    logger.warning(f"Geocode failed for {v.video_id}: {e}")

            props = {
                "video_id": v.video_id,
                "title": v.title,
                "restaurant": rest_name,
                "address": address,
                "city": city or ext.city,
                "country_code": country_code,
                "date_attempted": ext.date_attempted.isoformat() if hasattr(ext.date_attempted, "isoformat") else str(ext.date_attempted) if ext.date_attempted else None,
                "result": ext.result,
                "type": ext.challenge_type_slug,
                "thumbnail_url": v.thumbnail_url,
                "place_source": place_source,
            }

            if lat is not None and lng is not None:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                    "properties": props,
                })

            proto_rows.append(props)
            details.append({
                "video": {
                    "id": v.video_id,
                    "published_at": v.published_at.isoformat(),
                    "duration_seconds": v.duration_seconds,
                    "captions_available": v.captions_available,
                    "captions_path": captions_path,
                    "watch_url": f"https://www.youtube.com/watch?v={v.video_id}",
                },
                "extracted": {
                    "restaurant_name": ext.restaurant_name,
                    "city": ext.city,
                    "country": ext.country,
                    "date_attempted": props["date_attempted"],
                    "collaborators": ext.collaborators,
                    "result": ext.result,
                    "challenge_type_slug": ext.challenge_type_slug,
                    "confidence": ext.confidence,
                },
                "featured_place": {
                    "name": featured[0] if featured else None,
                    "lat": featured[1] if featured else None,
                    "lng": featured[2] if featured else None,
                },
                "geocode": {
                    "address": address,
                    "lat": lat,
                    "lng": lng,
                    "place_source": place_source,
                },
            })

        os.makedirs(out_dir, exist_ok=True)
        write_json(os.path.join(out_dir, "prototype.json"), {"rows": details})
        write_json(os.path.join(out_dir, "table.json"), {"rows": proto_rows})
        write_json(os.path.join(out_dir, "challenges.geojson"), {"type": "FeatureCollection", "features": features})
        logger.info(f"Prototype wrote {len(proto_rows)} rows, {len(features)} features to {out_dir}")
