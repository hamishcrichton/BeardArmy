"""Apply extraction-v2 results to the challenges table.

Updates result, challenge type, food_type, difficulty scores, source, and
confidence on existing challenges rows, keyed by video_id. Restaurants and
geocoding are left untouched. The DB is git-tracked, so `git checkout --
data/app.db` reverts everything.

Usage:
    PYTHONPATH=ingestion python -m bmf_ingest.apply_v2 [--dry-run] [--db data/app.db]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

V2_PATH = Path("data/derived/extractions_v2.jsonl")

SCORE_FIELDS = [
    "food_volume_score", "time_limit_score", "success_rate_score",
    "spiciness_score", "food_diversity_score", "risk_level_score",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply extraction v2 to challenges table")
    parser.add_argument("--db", default="data/app.db")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    records = [json.loads(l) for l in V2_PATH.open(encoding="utf-8") if l.strip()]
    print(f"{len(records)} v2 extractions loaded")

    conn = sqlite3.connect(args.db)
    type_ids = dict(conn.execute("SELECT slug, id FROM challenge_types"))

    before = Counter(r for (r,) in conn.execute("SELECT result FROM challenges"))
    print(f"before: {dict(before)}")

    updated = 0
    missing = []
    for rec in records:
        row = conn.execute(
            "SELECT id FROM challenges WHERE video_id = ?", (rec["video_id"],)
        ).fetchone()
        if row is None:
            missing.append(rec["video_id"])
            continue
        if not args.dry_run:
            conn.execute(
                """UPDATE challenges SET
                       result = ?, challenge_type_id = ?, food_type = ?,
                       food_volume_score = ?, time_limit_score = ?, success_rate_score = ?,
                       spiciness_score = ?, food_diversity_score = ?, risk_level_score = ?,
                       source = 'llm_v2', confidence = ?
                   WHERE video_id = ?""",
                (
                    rec["result"],
                    type_ids.get(rec.get("challenge_type")),  # 'unknown' -> NULL
                    rec.get("food_type"),
                    *(rec.get(f) for f in SCORE_FIELDS),
                    rec.get("confidence"),
                    rec["video_id"],
                ),
            )
        updated += 1

    if args.dry_run:
        after = Counter(r["result"] for r in records)
        print(f"dry-run: would update {updated} rows; v2 result distribution: {dict(after)}")
    else:
        conn.commit()
        after = Counter(r for (r,) in conn.execute("SELECT result FROM challenges"))
        print(f"updated {updated} rows; after: {dict(after)}")
    if missing:
        print(f"WARNING: {len(missing)} v2 records had no challenges row: {missing[:5]}...")
    conn.close()


if __name__ == "__main__":
    main()
