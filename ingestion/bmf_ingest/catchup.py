"""Bring extraction v2 up to date with the DB, then republish artifacts.

CI ingests new-video metadata nightly but cannot download captions (YouTube
bot-blocks datacenter IPs), so new challenges land with result=unknown. This
command runs from a residential IP and closes the gap end to end:

1. find videos in the DB with no v2 extraction yet
2. harvest their captions into data/raw/captions/
3. run extract_v2 on them
4. apply all v2 results to the challenges table
5. republish public/data artifacts

Safe to run any time; a no-op when everything is current. Commit and push
data/app.db + public/data afterwards to update the live site.

Usage:
    PYTHONPATH=ingestion python -m bmf_ingest.catchup [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

V2_PATH = Path("data/derived/extractions_v2.jsonl")


def run(module: str, *args: str) -> None:
    cmd = [sys.executable, "-m", f"bmf_ingest.{module}", *args]
    print(f">>> {' '.join(cmd[2:])}")
    env = {**os.environ, "PYTHONPATH": "ingestion", "DATABASE_URL": "sqlite:///./data/app.db"}
    subprocess.run(cmd, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description="Catch extraction v2 up with the DB")
    parser.add_argument("--db", default="data/app.db")
    parser.add_argument("--dry-run", action="store_true", help="Only report what would run")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    db_ids = {r[0] for r in conn.execute("SELECT video_id FROM videos")}
    stale = {
        r[0] for r in conn.execute("SELECT video_id FROM challenges WHERE source != 'llm_v2' OR source IS NULL")
    }
    conn.close()

    done = set()
    if V2_PATH.exists():
        with V2_PATH.open(encoding="utf-8") as f:
            done = {json.loads(l)["video_id"] for l in f if l.strip()}

    pending = sorted(db_ids - done)
    print(f"{len(db_ids)} videos in DB; {len(pending)} need v2 extraction; {len(stale)} challenges not yet on llm_v2")

    if not pending and not stale:
        print("Everything is current - nothing to do.")
        return
    if args.dry_run:
        print(f"would process: {pending[:10]}{'...' if len(pending) > 10 else ''}")
        return

    if pending:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="ascii") as f:
            f.write("\n".join(pending) + "\n")
            ids_file = f.name
        try:
            run("harvest_captions", "--ids", ids_file)
            run("extract_v2", "--only", ids_file)
        finally:
            os.unlink(ids_file)

    run("apply_v2")
    run("main", "publish", "--out", "./public/data")
    print("done - review changes, then commit data/app.db and public/data to update the site")


if __name__ == "__main__":
    main()
