from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.topics import TopicService


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate long-term topic notes.")
    parser.add_argument("--topic")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()
    if not args.topic and not args.all:
        parser.error("use --topic NAME or --all")
    service = TopicService()
    paths = (
        service.generate_all_topics(args.days)
        if args.all
        else [service.generate_topic(args.topic, args.days)]
    )
    for path in paths:
        print(f"[topic] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
