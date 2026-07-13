#!/usr/bin/env python3
"""Score an extraction run against the hand-labelled eval set.

Usage:
    python eval/run_eval.py data/derived/extractions_v2.jsonl
    python eval/run_eval.py --v1   # score the production DB (extraction v1) instead

Labels live in eval/labels.jsonl: {"video_id", "result", ...} where result is
the ground truth read from the transcript ending by a human/frontier-model
reviewer. Accuracy is reported on `result`, the field that drives every
downstream visual (win/loss record, streaks, maps).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

LABELS = Path(__file__).parent / "labels.jsonl"


def load_jsonl(path: Path) -> dict[str, dict]:
    out = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                out[rec["video_id"]] = rec
    return out


def load_v1(db: str = "data/app.db") -> dict[str, dict]:
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT video_id, result FROM challenges").fetchall()
    conn.close()
    return {vid: {"video_id": vid, "result": res} for vid, res in rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", nargs="?", help="Extraction JSONL to score")
    parser.add_argument("--v1", action="store_true", help="Score production DB (v1) instead")
    parser.add_argument("--db", default="data/app.db")
    args = parser.parse_args()

    labels = load_jsonl(LABELS)
    if args.v1:
        preds, name = load_v1(args.db), "v1 (production DB)"
    else:
        preds, name = load_jsonl(Path(args.predictions)), args.predictions

    scored = {vid: l for vid, l in labels.items() if vid in preds}
    missing = set(labels) - set(preds)
    if missing:
        print(f"WARNING: {len(missing)} labelled videos missing from predictions")

    correct = 0
    confusion: Counter = Counter()
    disagreements = []
    for vid, label in scored.items():
        truth, pred = label["result"], preds[vid]["result"]
        confusion[(truth, pred)] += 1
        if truth == pred:
            correct += 1
        else:
            disagreements.append((vid, truth, pred, preds[vid].get("result_evidence")))

    n = len(scored)
    print(f"== {name} ==")
    print(f"result accuracy: {correct}/{n} = {correct/n:.1%}" if n else "no overlap")

    # 'known rate': how often a definite result was produced (the v1 failure mode)
    known = sum(1 for v in scored if preds[v]["result"] != "unknown")
    print(f"definite result rate: {known}/{n} = {known/n:.1%}" if n else "")

    print("\nconfusion (truth -> predicted):")
    for (truth, pred), c in sorted(confusion.items()):
        marker = "" if truth == pred else "  <-- wrong"
        print(f"  {truth:8} -> {pred:8} : {c}{marker}")

    if disagreements:
        print("\ndisagreements:")
        for vid, truth, pred, ev in disagreements:
            print(f"  {vid}: truth={truth} pred={pred} evidence={ev!r}")


if __name__ == "__main__":
    main()
