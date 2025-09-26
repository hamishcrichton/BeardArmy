Ingestion Pipeline (Skeleton)

Overview
- Backfill and incremental ingest of BMF YouTube videos
- Extract restaurant, date, collaborators, result, challenge type
- Geocode restaurants; store to SQLite by default (schema in db/sqlite_init.sql)
- Publish JSON artifacts for map/table/dashboards

Commands
- Backfill: python -m bmf_ingest.main backfill --channel <CHANNEL_ID>
- Incremental: python -m bmf_ingest.main refresh --since-days 7 --channel <CHANNEL_ID>
- Publish: python -m bmf_ingest.main publish --out public/data

Environment
- Values are read from the process environment and .env (auto‑loaded via python‑dotenv).
- YOUTUBE_API_KEY: YouTube Data API v3 key
- YOUTUBE_CHANNEL_ID: default channel id
- DATABASE_URL: SQLite path (e.g. sqlite:///./data/app.db) or Postgres URL
- GEOCODER_PROVIDER: opencage|mapbox|nominatim
- GEOCODER_API_KEY: key/token for provider (if required)

SQLite Setup
- Initialize: `mkdir -p data && sqlite3 data/app.db < db/sqlite_init.sql`
- Use: ensure `.env` has `DATABASE_URL=sqlite:///./data/app.db`

Notes
- Captions via yt-dlp when available
- Idempotent upserts keyed by video_id and place_ref
- Confidence + source recorded for auditability
