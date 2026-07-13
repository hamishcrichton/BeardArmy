"""Rebuild restaurant identities from extraction v2 and geocode them.

v1 restaurant rows were built from regex extraction (names like "this week's
episode", city="BeardMeatsFood") and geocoded from those junk strings. This
pass builds venues from v2's restaurant_name/city/country_code, geocodes each
UNIQUE venue once via OpenCage (results cached in a geocode_cache table, so
re-runs cost zero API calls), and repoints challenges at the new rows.

Venue resolution ladder per video:
  1. restaurant_name + city  -> geocode "name, city" restricted to country
  2. low confidence / miss   -> geocode "city" alone, place_source llm_v2_approx
  3. no restaurant_name      -> challenge keeps its v1 restaurant link

Old v1 restaurant rows are left in place (orphans are harmless and keep
history); publish only joins via challenges.restaurant_id.

Usage:
    PYTHONPATH=ingestion python -m bmf_ingest.regeocode_v2 [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from pathlib import Path

import requests

V2_PATH = Path("data/derived/extractions_v2.jsonl")
OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"
MIN_CONFIDENCE = 5  # OpenCage confidence 1-10; below this we fall back to city level


def slugify(*parts: str | None) -> str:
    joined = "|".join((p or "").strip().lower() for p in parts)
    return re.sub(r"[^a-z0-9|]+", "-", joined).strip("-")


def ensure_cache(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS geocode_cache (
               query TEXT PRIMARY KEY,
               lat REAL, lng REAL, formatted TEXT, confidence INTEGER,
               status TEXT NOT NULL,
               created_at TEXT DEFAULT CURRENT_TIMESTAMP
           )"""
    )


class Geocoder:
    def __init__(self, conn: sqlite3.Connection, api_key: str):
        self.conn = conn
        self.api_key = api_key
        self.api_calls = 0

    def lookup(self, query: str, countrycode: str | None) -> dict:
        """Return {lat, lng, formatted, confidence, status} using cache first."""
        key = f"{query} [{countrycode or ''}]"
        row = self.conn.execute(
            "SELECT lat, lng, formatted, confidence, status FROM geocode_cache WHERE query = ?", (key,)
        ).fetchone()
        if row:
            return dict(zip(("lat", "lng", "formatted", "confidence", "status"), row))

        params = {"q": query, "key": self.api_key, "limit": 1, "no_annotations": 1}
        if countrycode:
            params["countrycode"] = countrycode.lower()
        resp = requests.get(OPENCAGE_URL, params=params, timeout=30)
        self.api_calls += 1
        time.sleep(1.05)  # free-tier rate limit: 1 req/s
        if resp.status_code in (401, 402, 429):
            raise RuntimeError(f"OpenCage HTTP {resp.status_code}: {resp.json().get('status', {}).get('message', '')}")
        resp.raise_for_status()
        results = resp.json().get("results") or []
        if results:
            r = results[0]
            out = {
                "lat": r["geometry"]["lat"], "lng": r["geometry"]["lng"],
                "formatted": r.get("formatted"), "confidence": r.get("confidence", 0),
                "status": "ok",
            }
        else:
            out = {"lat": None, "lng": None, "formatted": None, "confidence": 0, "status": "no_result"}
        self.conn.execute(
            "INSERT OR REPLACE INTO geocode_cache(query, lat, lng, formatted, confidence, status) VALUES (?,?,?,?,?,?)",
            (key, out["lat"], out["lng"], out["formatted"], out["confidence"], out["status"]),
        )
        self.conn.commit()
        return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild + geocode restaurants from v2 extractions")
    parser.add_argument("--db", default="data/app.db")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Max API lookups this run (0 = unlimited)")
    args = parser.parse_args()

    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    import os

    api_key = os.environ.get("GEOCODER_API_KEY", "")
    if not api_key and not args.dry_run:
        raise SystemExit("GEOCODER_API_KEY missing from environment/.env")

    records = [json.loads(l) for l in V2_PATH.open(encoding="utf-8") if l.strip()]

    # unique venues: slug -> representative fields + member video_ids
    venues: dict[str, dict] = {}
    skipped = 0
    for rec in records:
        name, city, cc = rec.get("restaurant_name"), rec.get("city"), rec.get("country_code")
        if not name:
            skipped += 1
            continue
        slug = slugify(name, city, cc)
        v = venues.setdefault(slug, {"name": name, "city": city, "cc": cc, "videos": []})
        v["videos"].append(rec["video_id"])

    print(f"{len(records)} extractions -> {len(venues)} unique venues; {skipped} videos have no restaurant name (unlink)")
    if args.dry_run:
        sample = list(venues.values())[:8]
        for v in sample:
            print(f"  e.g. {v['name']} | {v['city']} | {v['cc']} ({len(v['videos'])} videos)")
        return

    conn = sqlite3.connect(args.db)
    ensure_cache(conn)
    geo = Geocoder(conn, api_key)

    stats = {"venue_ok": 0, "city_fallback": 0, "no_coords": 0, "challenges_rewired": 0}
    try:
        for slug, v in venues.items():
            if args.limit and geo.api_calls >= args.limit:
                print(f"--limit {args.limit} API calls reached; run again to continue (cache persists)")
                break
            name, city, cc = v["name"], v["city"], v["cc"]

            place_source, lat, lng, formatted = "llm_v2", None, None, None
            q1 = ", ".join(p for p in (name, city) if p)
            hit = geo.lookup(q1, cc)
            if hit["status"] == "ok" and hit["confidence"] >= MIN_CONFIDENCE:
                lat, lng, formatted = hit["lat"], hit["lng"], hit["formatted"]
                stats["venue_ok"] += 1
            elif city:
                hit2 = geo.lookup(city, cc)
                if hit2["status"] == "ok":
                    lat, lng, formatted = hit2["lat"], hit2["lng"], hit2["formatted"]
                    place_source = "llm_v2_approx"
                    stats["city_fallback"] += 1
                else:
                    stats["no_coords"] += 1
            elif hit["status"] == "ok" and hit["lat"] is not None:
                # low-confidence venue hit but nothing better available
                lat, lng, formatted = hit["lat"], hit["lng"], hit["formatted"]
                place_source = "llm_v2_approx"
                stats["city_fallback"] += 1
            else:
                stats["no_coords"] += 1

            if lat is None:
                # keep map coverage: borrow coords from the videos' previous (v1) restaurant
                marks = ",".join("?" * len(v["videos"]))
                old = conn.execute(
                    f"""SELECT r.lat, r.lng FROM challenges c JOIN restaurants r ON r.id = c.restaurant_id
                        WHERE c.video_id IN ({marks}) AND r.lat IS NOT NULL LIMIT 1""",
                    v["videos"],
                ).fetchone()
                if old:
                    lat, lng = old
                    place_source = "llm_v2_inherited"
                    stats["no_coords"] -= 1
                    stats["inherited_coords"] = stats.get("inherited_coords", 0) + 1

            conn.execute(
                """INSERT INTO restaurants(name, place_source, place_ref, address, city, country_code, lat, lng)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(place_source, place_ref) DO UPDATE SET
                     name=excluded.name, address=excluded.address, city=excluded.city,
                     country_code=excluded.country_code, lat=excluded.lat, lng=excluded.lng""",
                (name, place_source, slug, formatted, city, cc, lat, lng),
            )
            (rid,) = conn.execute(
                "SELECT id FROM restaurants WHERE place_source=? AND place_ref=?", (place_source, slug)
            ).fetchone()
            marks = ",".join("?" * len(v["videos"]))
            cur = conn.execute(
                f"UPDATE challenges SET restaurant_id=? WHERE video_id IN ({marks})", (rid, *v["videos"])
            )
            stats["challenges_rewired"] += cur.rowcount
            conn.commit()
            done = stats["venue_ok"] + stats["city_fallback"] + stats["no_coords"]
            if done % 50 == 0:
                print(f"[{done}/{len(venues)}] {stats} | api_calls={geo.api_calls}")
        # Videos where v2 found no restaurant (home/candy videos) keep junk v1
        # links otherwise — unlink them so venue rankings and the map stay honest.
        nameless = [r["video_id"] for r in records if not r.get("restaurant_name")]
        if nameless:
            marks = ",".join("?" * len(nameless))
            cur = conn.execute(
                f"""UPDATE challenges SET restaurant_id = NULL
                    WHERE video_id IN ({marks})
                      AND restaurant_id NOT IN (SELECT id FROM restaurants WHERE place_source LIKE 'llm_v2%')""",
                nameless,
            )
            stats["unlinked_nameless"] = cur.rowcount
    finally:
        conn.commit()
        print(f"done: {stats} | api_calls={geo.api_calls}")
        conn.close()


if __name__ == "__main__":
    main()
