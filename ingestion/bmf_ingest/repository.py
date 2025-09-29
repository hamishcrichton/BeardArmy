from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Optional

from loguru import logger
from sqlalchemy import create_engine, text

from .models import Video, Restaurant, Challenge, Collaborator


class DbRepository:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, future=True)
        self.dialect = self.engine.dialect.name
        self.is_sqlite = self.dialect == "sqlite"

    @contextmanager
    def begin(self):
        with self.engine.begin() as conn:
            yield conn

    def upsert_video(self, v: Video):
        if self.is_sqlite:
            timestamp = "CURRENT_TIMESTAMP"
            sql = text(
                """
                INSERT INTO videos (video_id, title, description, published_at, duration_seconds,
                                    captions_available, playlist_ids, thumbnail_url, channel_id, raw_json, updated_at)
                VALUES (:video_id, :title, :description, :published_at, :duration_seconds,
                        :captions_available, :playlist_ids, :thumbnail_url, :channel_id, :raw_json, CURRENT_TIMESTAMP)
                ON CONFLICT(video_id) DO UPDATE SET
                  title = excluded.title,
                  description = excluded.description,
                  published_at = excluded.published_at,
                  duration_seconds = excluded.duration_seconds,
                  captions_available = excluded.captions_available,
                  playlist_ids = excluded.playlist_ids,
                  thumbnail_url = excluded.thumbnail_url,
                  channel_id = excluded.channel_id,
                  raw_json = excluded.raw_json,
                  updated_at = CURRENT_TIMESTAMP
                """
            )
            params = {
                "video_id": v.video_id,
                "title": v.title,
                "description": v.description,
                "published_at": v.published_at.isoformat() if hasattr(v.published_at, "isoformat") else str(v.published_at),
                "duration_seconds": v.duration_seconds,
                "captions_available": v.captions_available,
                "playlist_ids": json.dumps(v.playlist_ids or []),
                "thumbnail_url": v.thumbnail_url,
                "channel_id": v.channel_id,
                "raw_json": json.dumps(v.raw_json or {}),
            }
        else:
            sql = text(
                """
                INSERT INTO videos (video_id, title, description, published_at, duration_seconds,
                                    captions_available, playlist_ids, thumbnail_url, channel_id, raw_json, updated_at)
                VALUES (:video_id, :title, :description, :published_at, :duration_seconds,
                        :captions_available, :playlist_ids, :thumbnail_url, :channel_id, :raw_json, now())
                ON CONFLICT (video_id) DO UPDATE SET
                  title = EXCLUDED.title,
                  description = EXCLUDED.description,
                  published_at = EXCLUDED.published_at,
                  duration_seconds = EXCLUDED.duration_seconds,
                  captions_available = EXCLUDED.captions_available,
                  playlist_ids = EXCLUDED.playlist_ids,
                  thumbnail_url = EXCLUDED.thumbnail_url,
                  channel_id = EXCLUDED.channel_id,
                  raw_json = EXCLUDED.raw_json,
                  updated_at = now()
                """
            )
            params = {
                "video_id": v.video_id,
                "title": v.title,
                "description": v.description,
                "published_at": v.published_at,
                "duration_seconds": v.duration_seconds,
                "captions_available": v.captions_available,
                "playlist_ids": v.playlist_ids,
                "thumbnail_url": v.thumbnail_url,
                "channel_id": v.channel_id,
                "raw_json": v.raw_json,
            }
        with self.begin() as conn:
            conn.execute(sql, params)

    def upsert_restaurant(self, r: Restaurant) -> int:
        if self.is_sqlite:
            sql = text(
                """
                INSERT INTO restaurants
                  (name, address, city, region, country_code, phone, website, opening_hours, image_url,
                   status, lat, lng, place_source, place_ref, last_verified_at, updated_at)
                VALUES (:name, :address, :city, :region, :country_code, :phone, :website, :opening_hours, :image_url,
                        :status, :lat, :lng, :place_source, :place_ref, :last_verified_at, CURRENT_TIMESTAMP)
                ON CONFLICT(place_source, place_ref) DO UPDATE SET
                  name = COALESCE(excluded.name, restaurants.name),
                  address = COALESCE(excluded.address, restaurants.address),
                  city = COALESCE(excluded.city, restaurants.city),
                  region = COALESCE(excluded.region, restaurants.region),
                  country_code = COALESCE(excluded.country_code, restaurants.country_code),
                  phone = COALESCE(excluded.phone, restaurants.phone),
                  website = COALESCE(excluded.website, restaurants.website),
                  opening_hours = COALESCE(excluded.opening_hours, restaurants.opening_hours),
                  image_url = COALESCE(excluded.image_url, restaurants.image_url),
                  status = COALESCE(excluded.status, restaurants.status),
                  lat = COALESCE(excluded.lat, restaurants.lat),
                  lng = COALESCE(excluded.lng, restaurants.lng),
                  last_verified_at = COALESCE(excluded.last_verified_at, restaurants.last_verified_at),
                  updated_at = CURRENT_TIMESTAMP
                """
            )
            params = {
                "name": r.name,
                "address": r.address,
                "city": r.city,
                "region": r.region,
                "country_code": r.country_code,
                "phone": r.phone,
                "website": r.website,
                "opening_hours": json.dumps(r.opening_hours) if r.opening_hours is not None else None,
                "image_url": r.image_url,
                "status": r.status,
                "lat": r.lat,
                "lng": r.lng,
                "place_source": r.place_source,
                "place_ref": r.place_ref,
                "last_verified_at": r.last_verified_at,
            }
            with self.begin() as conn:
                conn.execute(sql, params)
                # Determine id: prefer unique key lookup when available
                if r.place_source and r.place_ref:
                    row = conn.execute(
                        text("SELECT id FROM restaurants WHERE place_source = :ps AND place_ref = :pr"),
                        {"ps": r.place_source, "pr": r.place_ref},
                    ).first()
                    if row:
                        return int(row[0])
                # Fallback to last inserted rowid (may be approximate if it was an update)
                row = conn.execute(text("SELECT last_insert_rowid()"))
                return int(list(row.fetchone())[0])
        else:
            sql = text(
                """
                INSERT INTO restaurants
                  (name, address, city, region, country_code, phone, website, opening_hours, image_url,
                   status, lat, lng, place_source, place_ref, last_verified_at, updated_at)
                VALUES (:name, :address, :city, :region, :country_code, :phone, :website, :opening_hours, :image_url,
                        :status, :lat, :lng, :place_source, :place_ref, :last_verified_at, now())
                ON CONFLICT (place_source, place_ref)
                  WHERE place_source IS NOT NULL AND place_ref IS NOT NULL
                DO UPDATE SET
                  name = COALESCE(EXCLUDED.name, restaurants.name),
                  address = COALESCE(EXCLUDED.address, restaurants.address),
                  city = COALESCE(EXCLUDED.city, restaurants.city),
                  region = COALESCE(EXCLUDED.region, restaurants.region),
                  country_code = COALESCE(EXCLUDED.country_code, restaurants.country_code),
                  phone = COALESCE(EXCLUDED.phone, restaurants.phone),
                  website = COALESCE(EXCLUDED.website, restaurants.website),
                  opening_hours = COALESCE(EXCLUDED.opening_hours, restaurants.opening_hours),
                  image_url = COALESCE(EXCLUDED.image_url, restaurants.image_url),
                  status = COALESCE(EXCLUDED.status, restaurants.status),
                  lat = COALESCE(EXCLUDED.lat, restaurants.lat),
                  lng = COALESCE(EXCLUDED.lng, restaurants.lng),
                  last_verified_at = COALESCE(EXCLUDED.last_verified_at, restaurants.last_verified_at),
                  updated_at = now()
                RETURNING id
                """
            )
            with self.begin() as conn:
                row = conn.execute(
                    sql,
                    {
                        "name": r.name,
                        "address": r.address,
                        "city": r.city,
                        "region": r.region,
                        "country_code": r.country_code,
                        "phone": r.phone,
                        "website": r.website,
                        "opening_hours": r.opening_hours,
                        "image_url": r.image_url,
                        "status": r.status,
                        "lat": r.lat,
                        "lng": r.lng,
                        "place_source": r.place_source,
                        "place_ref": r.place_ref,
                        "last_verified_at": r.last_verified_at,
                    },
                ).first()
                return int(row[0])

    def insert_challenge(self, c: Challenge) -> int:
        if self.is_sqlite:
            # Store time_limit as seconds (integer) in SQLite
            seconds = None
            if c.time_limit is not None:
                try:
                    seconds = int(c.time_limit.total_seconds())
                except Exception:
                    seconds = None
            sql = text(
                """
                INSERT INTO challenges
                  (video_id, restaurant_id, date_attempted, result, challenge_type_id, time_limit,
                   price_cents, notes, charity_flag, source, confidence)
                VALUES (:video_id, :restaurant_id, :date_attempted, :result,
                        (SELECT id FROM challenge_types WHERE slug = :type_slug),
                        :time_limit, :price_cents, :notes, :charity_flag, :source, :confidence)
                """
            )
            with self.begin() as conn:
                conn.execute(
                    sql,
                    {
                        "video_id": c.video_id,
                        "restaurant_id": c.restaurant_id,
                        "date_attempted": (c.date_attempted.isoformat() if hasattr(c.date_attempted, "isoformat") else (str(c.date_attempted) if c.date_attempted is not None else None)),
                        "result": c.result,
                        "type_slug": c.challenge_type_slug,
                        "time_limit": seconds,
                        "price_cents": c.price_cents,
                        "notes": c.notes,
                        "charity_flag": c.charity_flag,
                        "source": c.source,
                        "confidence": c.confidence,
                    },
                )
                row = self.engine.connect().execute(text("SELECT last_insert_rowid()")).first()
                return int(row[0])
        else:
            sql = text(
                """
                INSERT INTO challenges
                  (video_id, restaurant_id, date_attempted, result, challenge_type_id, time_limit,
                   price_cents, notes, charity_flag, source, confidence)
                VALUES (:video_id, :restaurant_id, :date_attempted, :result,
                        (SELECT id FROM challenge_types WHERE slug = :type_slug),
                        :time_limit, :price_cents, :notes, :charity_flag, :source, :confidence)
                RETURNING id
                """
            )
            with self.begin() as conn:
                row = conn.execute(
                    sql,
                    {
                        "video_id": c.video_id,
                        "restaurant_id": c.restaurant_id,
                        "date_attempted": c.date_attempted,
                        "result": c.result,
                        "type_slug": c.challenge_type_slug,
                        "time_limit": c.time_limit,
                        "price_cents": c.price_cents,
                        "notes": c.notes,
                        "charity_flag": c.charity_flag,
                        "source": c.source,
                        "confidence": c.confidence,
                    },
                ).first()
                return int(row[0])

    def get_challenge_id_by_video(self, video_id: str) -> Optional[int]:
        sql = text("SELECT id FROM challenges WHERE video_id = :video_id LIMIT 1")
        with self.engine.connect() as conn:
            row = conn.execute(sql, {"video_id": video_id}).first()
            return int(row[0]) if row else None
