# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BeardArmy is a data ingestion and visualization pipeline for BeardMeatsFood YouTube channel content. It extracts restaurant information, challenge details, and results from videos, geocodes locations, and publishes data for web-based map and table visualization.

## Key Commands

### Development Setup
```bash
# Install Python dependencies (use python3 explicitly)
pip install -r ingestion/requirements.txt

# Initialize SQLite database (default, no external DB required)
mkdir -p data && sqlite3 data/app.db < db/sqlite_init.sql

# Copy environment configuration
cp .env.example .env
# Then edit .env with your API keys
```

### Data Pipeline Operations
```bash
# Backfill all videos from channel
python3 -m bmf_ingest.main backfill --channel UCc9CjaAjsMMvaSghZB7-Kog

# Refresh recent videos (last 7 days by default)
python3 -m bmf_ingest.main refresh --since-days 7 --channel UCc9CjaAjsMMvaSghZB7-Kog

# Publish JSON artifacts for frontend
python3 -m bmf_ingest.main publish --out ./public/data

# Run prototype extraction (without DB, for testing)
python3 -m bmf_ingest.main prototype --channel UCc9CjaAjsMMvaSghZB7-Kog --limit 25 --out ./data --use-captions --use-geocode
```

### Local Development Server
```bash
# Run Flask app for preview (serves preview/index.html and data)
python3 application.py
# Then visit http://127.0.0.1:5000
```

### Testing
```bash
# Run tests with pytest
pytest -q
# Note: Test files go in ingestion/tests/ as test_*.py
```

## Architecture

### Core Pipeline Flow
1. **YouTube Client** (`youtube_client.py`): Fetches video metadata and captions via YouTube Data API and yt-dlp
2. **Extractors** (`extractors.py`): Parses titles, descriptions, and captions for restaurant info, dates, collaborators, results
3. **Featured Places** (`featured_places.py`): Maintains curated list of known restaurants with geocoded locations
4. **Geocoding** (`geocode.py`): Resolves restaurant addresses to coordinates via OpenCage/Mapbox/Nominatim
5. **Repository** (`repository.py`): Handles database operations with SQLAlchemy, supports both SQLite and PostgreSQL
6. **Pipeline** (`pipeline.py`): Orchestrates the full ingestion flow with backfill/refresh modes
7. **Publishing** (`publish.py`): Generates GeoJSON and table JSON for frontend consumption

### Database Schema
- Primary tables: `videos`, `places` (see `db/sqlite_init.sql` for SQLite, `db/001_init.sql` for PostgreSQL)
- Key relationships: Videos contain extracted place references stored in `places` table
- Idempotent upserts based on `video_id` and `place_ref` composite key

### Frontend Components
- Static preview in `preview/index.html` - no build step required, uses CDN dependencies
- Reusable React components in `frontend/components/` (Map.tsx, DataTable.tsx, Dashboard.tsx)
- Theme tokens in `frontend/styles/tokens.css` define BMF brand colors and styling

### Environment Configuration
Required environment variables (see `.env.example`):
- `YOUTUBE_API_KEY`: YouTube Data API v3 key
- `YOUTUBE_CHANNEL_ID`: Default channel ID (BeardMeatsFood: UCc9CjaAjsMMvaSghZB7-Kog)
- `DATABASE_URL`: SQLite path (sqlite:///./data/app.db) or PostgreSQL URL
- `GEOCODER_PROVIDER`: opencage|mapbox|nominatim
- `GEOCODER_API_KEY`: API key for geocoding provider
- `MAPTILER_KEY`: MapTiler key for map tiles in preview

## Important Patterns

### Extraction Confidence Levels
The pipeline tracks extraction confidence (0.0-1.0) and source for auditability:
- Title-only extraction: 0.5 confidence
- Description extraction: 0.6 confidence  
- Caption extraction: 0.7+ confidence
- Featured/curated places: 1.0 confidence

### Geocoding Fallback Chain
1. Check featured places for exact match
2. Try primary geocoding provider
3. Fall back to secondary providers if configured
4. Cache results to minimize API calls

### Idempotent Operations
All database operations use upserts to ensure idempotency - running the same command multiple times is safe and won't create duplicates.

## Python Environment
- Python 3.12+ required (use `python3` command explicitly)
- Virtual environment at `.venv/` (auto-created by PyCharm)
- Key dependencies: SQLAlchemy, pydantic, loguru, yt-dlp, google-api-python-client