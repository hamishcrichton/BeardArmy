"""Harvest raw caption files for all videos in the DB into a local raw store.

Designed to run from a residential IP (YouTube bot-blocks datacenter IPs, which
is why the CI pipeline has never successfully downloaded a caption). Fetch is
one-time per video: results land in data/raw/captions/<video_id>.<lang>.vtt and
a manifest records per-video outcomes so re-runs only attempt what's missing.

Usage:
    PYTHONPATH=ingestion python -m bmf_ingest.harvest_captions [--limit N] [--db data/app.db]
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import time
from pathlib import Path

import yt_dlp

RAW_DIR = Path("data/raw/captions")
MANIFEST = Path("data/raw/captions_manifest.jsonl")


def load_manifest() -> dict[str, dict]:
    entries: dict[str, dict] = {}
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    e = json.loads(line)
                    entries[e["video_id"]] = e
    return entries


def append_manifest(entry: dict) -> None:
    with MANIFEST.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def existing_vtt(video_id: str) -> Path | None:
    for p in RAW_DIR.glob(f"{video_id}.*.vtt"):
        return p
    return None


def download_one(video_id: str) -> dict:
    """Fetch English subs (manual or auto) in a single yt-dlp call."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-GB", "en-US"],
        "subtitlesformat": "vtt",
        "outtmpl": str(RAW_DIR / "%(id)s.%(ext)s"),
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "retries": 3,
        "socket_timeout": 30,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        return {"video_id": video_id, "status": "error", "error": str(e)[:300]}
    path = existing_vtt(video_id)
    if path is not None:
        return {"video_id": video_id, "status": "ok", "file": path.name}
    return {"video_id": video_id, "status": "no_captions"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest captions into data/raw/captions/")
    parser.add_argument("--db", default="data/app.db")
    parser.add_argument("--ids", help="File with one video_id per line; restrict the run to these")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N attempts (0 = all)")
    parser.add_argument("--min-sleep", type=float, default=1.0)
    parser.add_argument("--max-sleep", type=float, default=2.5)
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    conn = sqlite3.connect(args.db)
    video_ids = [r[0] for r in conn.execute("SELECT video_id FROM videos ORDER BY published_at")]
    conn.close()
    if args.ids:
        wanted = {l.strip() for l in Path(args.ids).read_text().splitlines() if l.strip()}
        video_ids = [v for v in video_ids if v in wanted]

    # Retry hard errors on re-runs, but never re-attempt confirmed no_captions/ok.
    pending = [
        v for v in video_ids
        if existing_vtt(v) is None and manifest.get(v, {}).get("status") != "no_captions"
    ]
    print(f"{len(video_ids)} videos in DB; {len(pending)} pending; {len(video_ids) - len(pending)} already resolved")

    counts = {"ok": 0, "no_captions": 0, "error": 0}
    attempted = 0
    for video_id in pending:
        if args.limit and attempted >= args.limit:
            break
        attempted += 1
        entry = download_one(video_id)
        append_manifest(entry)
        counts[entry["status"]] += 1
        if attempted % 25 == 0 or entry["status"] == "error":
            print(f"[{attempted}/{len(pending)}] {video_id}: {entry['status']} | totals {counts}")
        time.sleep(random.uniform(args.min_sleep, args.max_sleep))

    print(f"done: attempted={attempted} {counts}")


if __name__ == "__main__":
    main()
