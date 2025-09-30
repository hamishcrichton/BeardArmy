# Repository Guidelines

## Project Structure & Module Organization
- `ingestion/`: Python package `bmf_ingest` (pipelines, models, geocoding, YouTube client).
- `db/`: SQL schemas (`001_init.sql`, plus SQLite init).
- `frontend/`: Framework‑agnostic TSX components and theme tokens.
- `preview/`: Static HTML for local map/table preview.
- `docs/`: Setup notes and token audit. Copy `.env.example` to `.env`.
- Tests live under `ingestion/tests/` as `test_*.py`.

## Build, Test, and Development Commands
```bash
# Install ingestion deps
pip install -r ingestion/requirements.txt

# Initialize SQLite (default)
mkdir -p data && sqlite3 data/app.db < db/sqlite_init.sql

# (Optional) Initialize Postgres/PostGIS
psql -f db/001_init.sql "$DATABASE_URL"

# Backfill/refresh/publish data
python -m bmf_ingest.main backfill --channel <CHANNEL_ID>
python -m bmf_ingest.main refresh --since-days 7 --channel <CHANNEL_ID>
python -m bmf_ingest.main publish --out ./public/data
```
- Preview UI: open `preview/index.html` in a browser (no build step).

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indents; prefer type hints.
- Logging: use `loguru` (avoid `print`).
- Modules: `snake_case`; classes: `PascalCase`.
- Frontend: components in `frontend/components` as `PascalCase.tsx`; theme in `frontend/styles/tokens.css`.
- Config from environment; `.env.example` lists required vars.

## Testing Guidelines
- Framework: `pytest`. Place tests in `ingestion/tests/` named `test_*.py`.
- Run tests from repo root: `pytest -q`.
- Focus areas: extractor units, geocoding fallbacks, repository upserts.

## Commit & Pull Request Guidelines
- Commits: Conventional Commits (e.g., `feat: add refresh command`, `fix: handle missing captions`).
- PRs: include description, linked issues, setup/validation steps, and screenshots for UI‑visible changes.
- Scope changes narrowly; update docs (`docs/SETUP.md`, `.env.example`) when behavior/config changes.

## Security & Configuration Tips
- Never commit secrets. Use `.env` locally; CI/hosting injects `YOUTUBE_API_KEY`, `DATABASE_URL`, `GEOCODER_*`.
- Respect provider rate limits; cache geocodes where possible.
- Publishing writes JSON under `--out`; serve as static assets to the preview/frontend.
