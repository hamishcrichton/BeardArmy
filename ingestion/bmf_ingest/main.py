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

    # Prototype: sample extraction without DB, write artifacts directly
    p_proto = sub.add_parser("prototype")
    p_proto.add_argument("--channel", required=False)
    p_proto.add_argument("--limit", type=int, default=25)
    p_proto.add_argument("--out", required=True)
    p_proto.add_argument("--use-captions", action="store_true", help="Probe/download captions to enrich extraction")
    p_proto.add_argument("--use-geocode", action="store_true", help="Use geocoding when possible for coords")

    args = parser.parse_args()

    settings = Settings.load()
    pipe = Pipeline(settings)

    if args.cmd in {"backfill", "refresh"}:
        channel = getattr(args, "channel", None) or settings.youtube_channel_id
        if not channel:
            raise SystemExit("Channel ID must be supplied via --channel or YOUTUBE_CHANNEL_ID")
        if args.cmd == "backfill":
            pipe.backfill(channel)
        else:
            pipe.refresh(channel, since_days=args.since_days)
    elif args.cmd == "publish":
        pipe.publish(args.out)
    elif args.cmd == "prototype":
        channel = getattr(args, "channel", None) or settings.youtube_channel_id
        if not channel:
            raise SystemExit("Channel ID must be supplied via --channel or YOUTUBE_CHANNEL_ID")
        pipe.prototype(
            channel_id=channel,
            limit=args.limit,
            out_dir=args.out,
            use_captions=bool(args.use_captions),
            use_geocode=bool(args.use_geocode),
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
