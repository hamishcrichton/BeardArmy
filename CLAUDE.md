# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BeardArmy is a data ingestion and visualization pipeline for BeardMeatsFood YouTube channel content. It extracts restaurant information, challenge details, and results from videos, geocodes locations, and publishes JSON/GeoJSON artifacts for a web-based map and table view.

Data artifacts are committed to git: `data/app.db` (SQLite database) and `public/data/*` (published JSON) are refreshed daily by a scheduled GitHub Actions workflow that commits back to `main` (the recurring "chore(data): refresh published artifacts and persist DB" commits).

## Key Commands

The `bmf_ingest` package lives at `ingestion/bmf_ingest/` and is not installed (no pyproject/setup.py), so pipeline commands need `PYTHONPATH=ingestion` when run from the repo root.

### Setup
```bash
# Pipeline dependencies (root requirements.txt is web-deploy only — Flask + gunicorn)
pip install -r ingestion/requirements.txt

# Initialize SQLite database (default; no external DB required)
mkdir -p data && sqlite3 data/app.db < db/sqlite_init.sql
# For a pre-existing DB, apply migrations:
#   sqlite3 data/app.db < db/sqlite_add_challenge_scores.sql
#   sqlite3 data/app.db < db/sqlite_fix_restaurants_unique.sql

cp .env.example .env   # then fill in API keys
```

### Data Pipeline
```bash
# bash (PowerShell: $env:PYTHONPATH="ingestion" first, then run without the prefix)
PYTHONPATH=ingestion python -m bmf_ingest.main backfill --channel UCc9CjaAjsMMvaSghZB7-Kog
PYTHONPATH=ingestion python -m bmf_ingest.main refresh --since-days 7 --channel UCc9CjaAjsMMvaSghZB7-Kog
PYTHONPATH=ingestion python -m bmf_ingest.main publish --out ./public/data

# Prototype extraction without DB (writes prototype.json to --out)
PYTHONPATH=ingestion python -m bmf_ingest.main prototype --channel UCc9CjaAjsMMvaSghZB7-Kog --limit 25 --out ./data --use-captions --use-geocode
```
`--channel` falls back to `YOUTUBE_CHANNEL_ID` from the environment.

### Extraction v2 (transcript-based; run locally — CI cannot download captions)
```bash
# Catch up new videos end-to-end (harvest captions -> extract -> apply -> publish)
PYTHONPATH=ingestion python -m bmf_ingest.catchup [--dry-run]

# Individual steps
PYTHONPATH=ingestion python -m bmf_ingest.harvest_captions [--ids file]   # raw VTTs -> data/raw/captions/
PYTHONPATH=ingestion python -m bmf_ingest.extract_v2 [--only file]        # LLM extraction -> data/derived/extractions_v2.jsonl (needs ANTHROPIC_API_KEY in .env)
PYTHONPATH=ingestion python -m bmf_ingest.apply_v2 [--dry-run]            # write v2 results onto challenges table (weights, collaborators)
PYTHONPATH=ingestion python -m bmf_ingest.regeocode_v2 [--dry-run]        # rebuild venues from v2 names + geocode (cached in geocode_cache table; needs GEOCODER_API_KEY)

# Score an extraction run against the 75-video ground-truth set
python eval/run_eval.py data/derived/extractions_v2.jsonl
python eval/run_eval.py --v1   # score whatever is in the DB
```
Commit `data/app.db` + `public/data` after a catchup to update the live site. CI runs with `USE_LLM_EXTRACTION=false` (repo variable): new videos land as result=unknown until a local catchup corrects them.

### Local Preview Server
```bash
python application.py   # Flask, serves preview/ at http://127.0.0.1:5000 and artifacts at /public/data/<file>
```

### Testing
There is no pytest harness (no config, no conftest, pytest not in requirements). Tests are standalone scripts in the repo root that do their own `sys.path` setup — run directly:
```bash
python test_extraction.py
python test_llm_extraction.py   # etc.: test_caption_download, test_enhanced_extraction, test_extractor_standalone, test_improved_extraction
```

## Architecture

### Pipeline flow (`ingestion/bmf_ingest/`)
`main.py` (argparse CLI: backfill/refresh/publish/prototype) → `pipeline.py` (`Pipeline`, the orchestrator). Per video:

1. **`youtube_client.py`** — fetches metadata via YouTube Data API v3 (snippet, contentDetails, recordingDetails, localizations, topicDetails) and downloads captions via yt-dlp into `<DATA_DIR>/captions/`.
2. **`caption_parser.py`** — parses VTT/SRT captions into a bounded transcript intro (`extract_caption_intro`).
3. **Extraction** — `extractors.py` (regex/heuristics over title, description, tags) always runs; if `USE_LLM_EXTRACTION=true`, `llm_extractor.py` (Anthropic or OpenAI, strict-JSON prompt over transcript + metadata, includes 6 difficulty scores 0–10) runs too and **its values override the regex values**. Challenge `source` is `"llm"` or `"auto"`.
4. **Location resolution** (priority chain in `pipeline.py`): YouTube `recordingDetails` coords (`place_source="youtube_recording"`) → `featured_places.py` (`place_source="youtube_featured"`) → `geocode.py` on "restaurant city country" → city/country centroid (`place_source="approx"`).
5. **`repository.py`** — SQLAlchemy Core with dialect-branched SQL for SQLite and PostgreSQL.
6. **`publish.py`** + `Pipeline.publish` — one big challenges⋈restaurants⋈videos join → writes `challenges.geojson` (only rows with coords), `table.json` (all rows), `index.json` to `--out` (always `./public/data`). Optional `PUBLISH_LIMIT` env caps rows.

Notes on step 4: `featured_places.py` is **not a curated list** — it live-scrapes the YouTube watch-page HTML for a Google Maps "featured places" link. `geocode.py` only implements **OpenCage**; other `GEOCODER_PROVIDER` values silently return no coords. There is no geocode cache — re-geocoding is avoided only because already-processed videos are skipped.

### Database
Tables (see `db/sqlite_init.sql`): `videos`, `restaurants`, `challenge_types` (seeded: quantity/spicy/speed/mixed), `challenges`, `collaborators`, `challenge_collaborators`, `tags`, `challenge_tags`.

- Upserts: `videos` on `video_id`; `restaurants` on `(place_source, place_ref)` with COALESCE (fills nulls, never overwrites non-null).
- **`challenges` are insert-if-absent, never updated** — re-running the pipeline will not refresh result/scores for already-processed videos. To re-extract, delete the challenge rows first.
- SQLite (`data/app.db`) is the maintained path. The PostgreSQL schema (`db/001_init.sql`) lags SQLite — it lacks `food_type` and the six score columns, so publish would fail on Postgres.

### Frontend
- `preview/` is the real UI: five static pages (index, map, analytics, collaborators, shame), no build step, shared contract in `preview/assets/app.js` + `app.css`, MapLibre GL via CDN. The MapTiler key lives in `preview/assets/config.js` (client-visible by design; abuse guarded by origin restriction in the MapTiler dashboard, not secrecy). Data via `../public/data/*.json`. Styled by `frontend/styles/tokens.css` ("Butcher's Paper" tokens).
- `frontend/components/` (Map.tsx, DataTable.tsx, Dashboard.tsx) is an **unused Next.js-ready scaffold** — no package.json, nothing imports it.

### Deployment
**Cloudflare Workers static assets, git-connected, serving the repo root** — live at **https://beardarmy.uk/** (custom domain; `www.beardarmy.uk` also bound). The Worker's own URL `https://beardarmy.hamish-a20.workers.dev/` still resolves as the origin. Both custom domains are Worker custom-domain bindings on the `beardarmy.uk` Cloudflare zone (registered via Cloudflare Registrar, so DNS + SSL are automatic). The dashboard "Connect to Git" flow creates a *Worker*, not a classic Pages project. Config is `wrangler.jsonc` (`assets.directory: "./"`), deploy command `npx wrangler deploy`. Same layout the local dev server uses (`python -m http.server 8123`). Root `_redirects` sends `/` → `/preview/` (301); `index.html` is a meta-refresh fallback. Every push to `main` (including the nightly CI data commit) auto-redeploys. The footer/meta/favicon are injected via `preview/assets/app.js` + per-page head tags.

Two deploy gotchas (each cost a failed build to learn):
- **`_redirects` must target `/preview/`, not `/preview/index.html`** — the static-asset handler auto-strips `.html`/`/index`, so a target ending in `index.html` is rejected as an infinite loop (`code 100324`).
- **`.assetsignore` uses gitignore semantics** — an unanchored `data/` matches at *any* depth and silently drops `public/data/` (the published JSON the site fetches), yielding a styled site with every stat at 0. Anchor root-only excludes with a leading slash (`/data/`).
- Each build wastes ~3 min installing Flask/gunicorn because `runtime.txt`+`requirements.txt` make Cloudflare auto-detect a Python project; harmless but eats build minutes daily. The map's MapTiler key is currently unrestricted — origin-restrict it to `beardarmy.uk`, `www.beardarmy.uk` (+ the workers.dev host and localhost) in the MapTiler dashboard.

Legacy: `application.py` (Flask) + `Procfile` + root `requirements.txt` + `runtime.txt` are from an earlier Elastic-Beanstalk-style plan; dormant, not used by the Worker.

## CI / Automation

`.github/workflows/refresh_publish.yml` ("Refresh and Publish Artifacts"):
- Runs daily at 03:00 UTC, plus `workflow_dispatch` with inputs `mode` (refresh|backfill), `since_days`, `channel_id`.
- Python 3.11, `PYTHONPATH: ingestion`, SQLite; initializes the DB if missing, otherwise applies both migration files.
- Runs ingest then publish, then force-commits `public/data` and `data/app.db` to `main` as the github-actions bot.
- Secrets/vars consumed: `YOUTUBE_API_KEY`, `GEOCODER_PROVIDER`/`GEOCODER_API_KEY`, `USE_LLM_EXTRACTION`, `LLM_PROVIDER`, `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`.

## Environment Configuration

Loaded by `ingestion/bmf_ingest/config.py`; `.env` is auto-loaded via python-dotenv (see `.env.example`):
- `YOUTUBE_API_KEY`, `YOUTUBE_CHANNEL_ID` (BeardMeatsFood: `UCc9CjaAjsMMvaSghZB7-Kog`)
- `DATABASE_URL` (`sqlite:///./data/app.db` or a PostgreSQL URL)
- `GEOCODER_PROVIDER` (only `opencage` is implemented), `GEOCODER_API_KEY`
- `DATA_DIR` (default `./data`; captions land in `<DATA_DIR>/captions/`)
- `USE_LLM_EXTRACTION` (default false), `LLM_PROVIDER` (`anthropic`|`openai`), `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`, `LLM_MODEL` (optional override)
- `PUBLISH_LIMIT` (optional row cap for publish)
- `MAPTILER_KEY` — used by the preview map only, not read by config.py

## Gotchas

- Caption downloads use yt-dlp with `player_client=android` and a random 2–5 s sleep per video to dodge bot detection — backfills are slow and network-fragile.
- Featured-places scraping parses live YouTube watch-page HTML — breaks silently when YouTube changes markup.
- The default LLM model in `llm_extractor.py` is the outdated `claude-3-haiku-20240307`; prefer setting `LLM_MODEL`.
- Extraction confidence is a weighted formula in `extractors.py` (restaurant/result/type components), not fixed per-source values; the LLM returns its own confidence.
- The ~15 loose `*.md`/`*.txt` files in the repo root are historical design/status notes, not authoritative docs.
