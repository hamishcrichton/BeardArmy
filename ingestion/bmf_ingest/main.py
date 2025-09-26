from __future__ import annotations

import argparse
from loguru import logger

from .config import Settings
from .pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description="BMF ingestion pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_backfill = sub.add_parser("backfill")
    p_backfill.add_argument("--channel", required=False)

    p_refresh = sub.add_parser("refresh")
    p_refresh.add_argument("--channel", required=False)
    p_refresh.add_argument("--since-days", type=int, default=7)

    p_publish = sub.add_parser("publish")
    p_publish.add_argument("--out", required=True)

    args = parser.parse_args()

    settings = Settings.load()
    pipe = Pipeline(settings)
    channel = args.channel or settings.youtube_channel_id
    if args.cmd in {"backfill", "refresh"} and not channel:
        raise SystemExit("Channel ID must be supplied via --channel or YOUTUBE_CHANNEL_ID")

    if args.cmd == "backfill":
        pipe.backfill(channel)
    elif args.cmd == "refresh":
        pipe.refresh(channel, since_days=args.since_days)
    elif args.cmd == "publish":
        pipe.publish(args.out)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

