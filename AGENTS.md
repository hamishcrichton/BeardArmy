# Repository Guidelines

## Project Structure & Module Organization
- `ingestion/`: Python package `bmf_ingest` (pipelines, models, geocoding, YouTube client).
- `db/`: Postgres/PostGIS schema (`001_init.sql`).
- `frontend/`: Framework‑agnostic TSX components and theme tokens.
- `preview/`: Static HTML for local map/table preview.
- `docs/`: Setup notes and token audit. See `.env.example` for required env vars.

## Build, Test, and Development Commands
- Install ingestion deps: `pip install -r ingestion/requirements.txt`.
- Init SQLite (default): `mkdir -p data && sqlite3 data/app.db < db/sqlite_init.sql`.
- Init Postgres (optional): `psql -f db/001_init.sql "$DATABASE_URL"`.
- Backfill videos: `python -m bmf_ingest.main backfill --channel <CHANNEL_ID>`.
- Incremental refresh: `python -m bmf_ingest.main refresh --since-days 7 --channel <CHANNEL_ID>`.
- Publish artifacts: `python -m bmf_ingest.main publish --out ./public/data`.
- Preview UI: open `preview/index.html` in a browser (no build required).

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indents; prefer type hints. Modules use `snake_case`, classes `PascalCase`.
- Logging: use `loguru` (avoid `print`).
- Config: read from environment; copy `.env.example` to `.env` for local use.
- Frontend: components in `frontend/components` are `PascalCase.tsx`; theme in `frontend/styles/tokens.css`.

## Testing Guidelines
- Framework: `pytest` (not included yet). Place tests in `ingestion/tests/` named `test_*.py`.
- Run tests: `pytest -q` from repo root.
- Focus: extractor units, geocoding fallbacks, repository upserts.

## Commit & Pull Request Guidelines
- Commits: use Conventional Commits (e.g., `feat: add refresh command`, `fix: handle missing captions`).
- PRs: include a clear description, linked issues, setup/validation steps, and screenshots for UI‑visible changes.
- Scope: keep changes focused; update docs (`docs/SETUP.md`, `.env.example`) when behavior/config changes.

## Security & Configuration Tips
- Do not commit secrets. Use `.env` locally; CI/hosting should inject `YOUTUBE_API_KEY`, `DATABASE_URL`, `GEOCODER_*`.
- Respect provider rate limits; cache geocodes when possible.
- Publishing writes JSON under `--out`; serve those as static assets to `frontend/preview`.
