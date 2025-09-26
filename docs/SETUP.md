Setup Guide (Local Preview, Providers, Ingestion)

Providers
- Map tiles: MapTiler (recommended)
  - Create a free account, get an API key.
  - Style URL (MapLibre): https://api.maptiler.com/maps/streets/style.json?key=YOUR_KEY
- Geocoding: OpenCage
  - Create a key, set env GEOCODER_PROVIDER=opencage and GEOCODER_API_KEY.

Preview (no build needed)
1) Open preview/index.html in a browser.
2) Paste your MapTiler key and click "Load Map". This uses demo data baked into the page.

Next.js App (optional)
- Import frontend/styles/tokens.css globally to pick up BMF theme aliases.
- Use components in frontend/components (Map, DataTable, Dashboard) and feed them JSON artifacts.

Ingestion
1) Create a Postgres database (Supabase or local) and run db/001_init.sql.
2) Set env vars (see .env.example).
3) Install Python deps: pip install -r ingestion/requirements.txt
4) Backfill: python -m bmf_ingest.main backfill --channel YOUTUBE_CHANNEL_ID
5) Publish artifacts: python -m bmf_ingest.main publish --out ./public/data

Notes
- Respect YouTube and provider ToS. Cache geocodes to minimize cost.
- The preview uses CDN scripts; production should bundle dependencies.

