"""Classify verdict-pending videos as challenge vs special (non-challenge).

Most videos without a win/loss verdict are not failed extractions - they are
music videos, Q&As, cheat days, food tours, milestones. This mini-pass asks
the LLM to classify ONLY the pending videos (cheap: ~60 calls) and records
the result in data/derived/video_kinds.jsonl. apply_kinds() then writes
challenges.kind ('challenge' | 'special'); everything with a win/loss verdict
is a challenge by definition and keeps the default.

Usage:
    PYTHONPATH=ingestion python -m bmf_ingest.classify_kind [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from .extract_v2 import find_caption, parse_caption_segments, transcript_windows

OUT_PATH = Path("data/derived/video_kinds.jsonl")

SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {
            "type": "string",
            "enum": ["challenge", "special"],
            "description": "challenge = a win/lose eating challenge or eating contest attempt; special = anything else",
        },
        "category": {
            "type": "string",
            "enum": ["music_video", "milestone", "qa_or_interview", "cheat_day_or_mukbang",
                     "food_tour", "vlog_or_bts", "contest", "challenge", "other"],
        },
        "reason": {"type": "string", "description": "One short sentence"},
        "confidence": {"type": "number"},
    },
    "required": ["kind", "category", "reason", "confidence"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You classify videos from the BeardMeatsFood YouTube channel (competitive eater).

kind = "challenge": the video's core content is attempting a defined eating challenge or eating
contest with a pass/fail or win/lose outcome (even if the outcome is never revealed on camera).
kind = "special": everything else - music videos, subscriber-milestone videos, Q&As/interviews,
cheat days, mukbangs/banquets with no pass-fail stakes, "24 hours eating at..." food tours,
diet recreations, behind-the-scenes/vlogs.

Judge from the title, description and transcript. A cheat-day or tour video often EATS a lot
without any defined challenge: that is "special". An eating CONTEST (vs other eaters) counts
as "challenge" with category "contest"."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/app.db")
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    import anthropic

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    pending = [dict(r) for r in conn.execute(
        """SELECT c.video_id, v.title, v.description FROM challenges c
           JOIN videos v ON v.video_id = c.video_id WHERE c.result = 'unknown'"""
    )]

    done = set()
    if OUT_PATH.exists():
        done = {json.loads(l)["video_id"] for l in OUT_PATH.open(encoding="utf-8") if l.strip()}
    todo = [p for p in pending if p["video_id"] not in done]
    print(f"{len(pending)} pending videos; {len(todo)} to classify")

    client = anthropic.Anthropic()
    counts = {"challenge": 0, "special": 0}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("a", encoding="utf-8") as out:
        for i, v in enumerate(todo):
            if args.limit and i >= args.limit:
                break
            cap = find_caption(v["video_id"])
            windows = transcript_windows(parse_caption_segments(cap), 400, 250) if cap else None
            parts = [f"Title: {v['title']}", f"Description:\n{(v['description'] or '')[:800]}"]
            if windows and windows["total_words"]:
                parts.append(f"Transcript start:\n{windows['intro']}")
                parts.append(f"Transcript end:\n{windows['ending']}")
            response = client.messages.create(
                model=args.model, max_tokens=300, system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": "\n\n".join(parts)}],
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
            )
            data = json.loads(next(b.text for b in response.content if b.type == "text"))
            out.write(json.dumps({"video_id": v["video_id"], "title": v["title"], **data}, ensure_ascii=False) + "\n")
            out.flush()
            counts[data["kind"]] += 1
    print(f"done: {counts}")

    # apply: kind column (default challenge), specials flagged
    cols = [r[1] for r in conn.execute("PRAGMA table_info(challenges)")]
    if "kind" not in cols:
        conn.execute("ALTER TABLE challenges ADD COLUMN kind TEXT DEFAULT 'challenge'")
    specials = [json.loads(l)["video_id"] for l in OUT_PATH.open(encoding="utf-8")
                if l.strip() and json.loads(l)["kind"] == "special"]
    conn.execute("UPDATE challenges SET kind = 'challenge' WHERE kind IS NULL")
    if specials:
        marks = ",".join("?" * len(specials))
        conn.execute(f"UPDATE challenges SET kind = 'special' WHERE video_id IN ({marks})", specials)
    conn.commit()
    print("applied:", dict(conn.execute("SELECT kind, COUNT(*) FROM challenges GROUP BY kind")))


if __name__ == "__main__":
    main()
