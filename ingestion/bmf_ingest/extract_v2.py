"""Extraction v2: LLM extraction over full-transcript windows (intro + ENDING).

Fixes the two defects that left 67% of results "unknown" in v1:
1. v1 never had captions in CI (bot-blocked); v2 reads locally harvested VTTs
   from data/raw/captions/.
2. v1 truncated the transcript to the first 400s while its own prompt said the
   ending is the only reliable source for the result; v2 sends intro + ending.

Results are written to data/derived/extractions_v2.jsonl (one JSON object per
video, tagged with extractor_version and model). The production DB is never
touched. Re-runs skip video_ids already present, so the job is resumable.

Usage:
    PYTHONPATH=ingestion python -m bmf_ingest.extract_v2 [--limit N]
        [--only ids.txt] [--model claude-haiku-4-5] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

EXTRACTOR_VERSION = 2
RAW_CAPTIONS = Path("data/raw/captions")
OUT_PATH = Path("data/derived/extractions_v2.jsonl")

# $ per MTok (input, output) for cost reporting
PRICES = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
}

# --- Caption parsing -------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_INLINE_TIMING_RE = re.compile(r"<\d{2}:\d{2}:\d{2}[.,]\d+>")
_CUE_TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[.,]\d*\s*-->")
_NOISE_RE = re.compile(r"\[[^\]]*\]|[♪♫]")


def parse_caption_segments(path: Path) -> list[tuple[float, str]]:
    """Parse a VTT/SRT file into (start_seconds, text) segments.

    YouTube auto-captions use a rolling two-line window: each cue repeats the
    previous line as plain text and carries the NEW words with inline timing
    tags (<00:00:02.080><c> way</c>). For those files only tagged lines are
    kept. Manual captions have no inline tags; all cue text is kept with
    consecutive-duplicate suppression.
    """
    content = path.read_text(encoding="utf-8", errors="replace")
    is_auto = "<c>" in content or _INLINE_TIMING_RE.search(content) is not None

    segments: list[tuple[float, str]] = []
    current_time = 0.0
    prev_text = None
    for line in content.splitlines():
        line = line.strip()
        m = _CUE_TIME_RE.match(line)
        if m:
            current_time = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            continue
        if not line or line == "WEBVTT" or line.startswith(("Kind:", "Language:", "NOTE")) or line.isdigit():
            continue
        if is_auto and not (_INLINE_TIMING_RE.search(line) or "<c>" in line):
            continue  # plain re-display of the previous line
        text = _NOISE_RE.sub("", _TAG_RE.sub("", line))
        text = re.sub(r"\s+", " ", text).strip()
        if not text or text == prev_text:
            continue
        prev_text = text
        segments.append((current_time, text))
    return segments


def transcript_windows(
    segments: list[tuple[float, str]], intro_words: int = 800, ending_words: int = 500
) -> dict:
    words: list[str] = []
    for _, text in segments:
        words.extend(text.split())
    intro = " ".join(words[:intro_words])
    ending = " ".join(words[-ending_words:])
    return {
        "intro": intro,
        "ending": ending,
        "total_words": len(words),
        "duration_seconds": segments[-1][0] if segments else 0,
    }


# --- LLM extraction --------------------------------------------------------

SCHEMA = {
    "type": "object",
    "properties": {
        "restaurant_name": {"type": ["string", "null"]},
        "city": {"type": ["string", "null"]},
        "country_code": {
            "type": ["string", "null"],
            "description": "ISO 3166-1 alpha-2, e.g. GB, US, IE",
        },
        "result": {"type": "string", "enum": ["success", "failure", "unknown"]},
        "result_evidence": {
            "type": ["string", "null"],
            "description": "Short verbatim quote from the transcript ending that proves the result",
        },
        "challenge_type": {
            "type": "string",
            "enum": ["quantity", "spicy", "speed", "mixed", "unknown"],
        },
        "food_type": {"type": ["string", "null"]},
        "food_volume_score": {"type": "integer"},
        "time_limit_score": {"type": "integer"},
        "success_rate_score": {"type": "integer"},
        "spiciness_score": {"type": "integer"},
        "food_diversity_score": {"type": "integer"},
        "risk_level_score": {"type": "integer"},
        "confidence": {"type": "number"},
    },
    "required": [
        "restaurant_name", "city", "country_code", "result", "result_evidence",
        "challenge_type", "food_type", "food_volume_score", "time_limit_score",
        "success_rate_score", "spiciness_score", "food_diversity_score",
        "risk_level_score", "confidence",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You extract structured data from videos on the BeardMeatsFood YouTube channel, \
where competitive eater Adam Moran attempts restaurant food challenges (usually "finish it and it's free").

Rules for the `result` field — this is the most important output:
- The TRANSCRIPT ENDING is the only reliable source. The result is revealed in the final minutes.
- success: he finished the challenge. Typical phrasing: "my name goes on the wall", "got it done", \
"beat the challenge", "that means it's free", "demolished it", stating the finish time.
- failure: he did not finish. Typical phrasing: "I'm tapping out", "this one's beaten me", \
"I couldn't do it", "I'm going to have to pay", "first defeat in a while".
- unknown: ONLY when the ending is missing or genuinely never states the outcome.
- NEVER infer the result from the title — titles are deliberate clickbait and often imply failure for videos he wins.
- Quote the decisive sentence verbatim in result_evidence (null only if result is unknown).

Other fields:
- restaurant_name / city / country_code: the venue where the challenge takes place. Use the description \
and intro; country_code is ISO 3166-1 alpha-2 (UK videos = GB).
- challenge_type: quantity (volume of food), spicy (heat-based), speed (time-critical), mixed, or unknown.
- Scores are integers 0-10: food_volume_score (amount of food), time_limit_score (10 = very tight limit, \
0 = no limit), success_rate_score (how rarely others complete it, 10 = nobody has), spiciness_score, \
food_diversity_score (variety of components), risk_level_score (overall difficulty).
- confidence: 0.0-1.0, your overall confidence in the extraction."""


def build_user_prompt(video: dict, windows: dict | None) -> str:
    desc = (video.get("description") or "")[:1500]
    parts = [
        f"Video title: {video['title']}",
        f"Published: {video.get('published_at') or 'unknown'}",
        f"Description:\n{desc}",
    ]
    if windows and windows["total_words"] > 0:
        parts.append(
            f"Transcript intro (first ~800 words of {windows['total_words']} total):\n{windows['intro']}"
        )
        parts.append(
            f"Transcript ENDING (final ~500 words — the result is revealed here):\n{windows['ending']}"
        )
    else:
        parts.append("No transcript is available for this video. Set result to unknown "
                     "unless the description itself states the outcome.")
    parts.append("Extract the structured data now.")
    return "\n\n".join(parts)


def find_caption(video_id: str) -> Path | None:
    for p in RAW_CAPTIONS.glob(f"{video_id}.*.vtt"):
        return p
    return None


def load_done() -> set[str]:
    done = set()
    if OUT_PATH.exists():
        with OUT_PATH.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    done.add(json.loads(line)["video_id"])
    return done


def main() -> None:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    parser = argparse.ArgumentParser(description="Run extraction v2 over harvested captions")
    parser.add_argument("--db", default="data/app.db")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", help="File with one video_id per line; restrict the run to these")
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--dry-run", action="store_true", help="Print the prompt for the first pending video and exit")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    videos = [dict(r) for r in conn.execute(
        "SELECT video_id, title, description, published_at FROM videos ORDER BY published_at"
    )]
    conn.close()

    if args.only:
        wanted = {l.strip() for l in Path(args.only).read_text().splitlines() if l.strip()}
        videos = [v for v in videos if v["video_id"] in wanted]

    done = load_done()
    pending = [v for v in videos if v["video_id"] not in done]
    print(f"{len(videos)} videos in scope; {len(pending)} pending; {len(done)} already extracted")

    if args.dry_run:
        v = pending[0]
        cap = find_caption(v["video_id"])
        windows = transcript_windows(parse_caption_segments(cap)) if cap else None
        print(f"--- SYSTEM ---\n{SYSTEM_PROMPT}\n--- USER ({v['video_id']}) ---\n{build_user_prompt(v, windows)}")
        return

    import anthropic  # deferred so --dry-run works without a key

    client = anthropic.Anthropic()
    in_price, out_price = PRICES.get(args.model, (5.0, 25.0))
    tokens_in = tokens_out = 0
    counts = {"success": 0, "failure": 0, "unknown": 0, "error": 0, "no_captions": 0}

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    attempted = 0
    with OUT_PATH.open("a", encoding="utf-8") as out:
        for v in pending:
            if args.limit and attempted >= args.limit:
                break
            attempted += 1
            cap = find_caption(v["video_id"])
            windows = transcript_windows(parse_caption_segments(cap)) if cap else None
            if windows is None:
                counts["no_captions"] += 1
            try:
                response = client.messages.create(
                    model=args.model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": build_user_prompt(v, windows)}],
                    output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
                )
            except anthropic.APIStatusError as e:
                counts["error"] += 1
                print(f"[{attempted}/{len(pending)}] {v['video_id']}: API error {e.status_code}: {e.message}")
                continue
            if response.stop_reason == "refusal":
                counts["error"] += 1
                print(f"[{attempted}/{len(pending)}] {v['video_id']}: refusal")
                continue
            tokens_in += response.usage.input_tokens
            tokens_out += response.usage.output_tokens
            data = json.loads(next(b.text for b in response.content if b.type == "text"))
            record = {
                "video_id": v["video_id"],
                "title": v["title"],
                "extractor_version": EXTRACTOR_VERSION,
                "model": args.model,
                "had_captions": windows is not None and windows["total_words"] > 0,
                "transcript_words": windows["total_words"] if windows else 0,
                **data,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            counts[data["result"]] += 1
            if attempted % 25 == 0:
                cost = (tokens_in * in_price + tokens_out * out_price) / 1e6
                print(f"[{attempted}/{len(pending)}] {counts} | ~${cost:.2f}")

    cost = (tokens_in * in_price + tokens_out * out_price) / 1e6
    print(f"done: attempted={attempted} {counts}")
    print(f"tokens: in={tokens_in} out={tokens_out} | estimated cost ${cost:.2f} ({args.model})")


if __name__ == "__main__":
    main()
