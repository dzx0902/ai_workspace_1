from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.pipeline import fetch_sources
from paper_radar.sources.registry import FETCHERS, normalize_source_type
from paper_radar.utils import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch configured paper sources.")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--source",
        help="Source type, for example arxiv, biorxiv, pubmed, or openreview.",
    )
    selection.add_argument("--all", action="store_true", help="Fetch all enabled sources.")
    parser.add_argument("--limit", type=int, help="Maximum papers fetched per source.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.source:
        normalized = normalize_source_type(args.source)
        if normalized not in FETCHERS:
            parser.error(
                f"unsupported --source {args.source!r}; "
                f"choose from: {', '.join(sorted(FETCHERS))}"
            )

    setup_logging(args.verbose)
    stats = fetch_sources(
        source_type=args.source,
        limit=args.limit,
        include_disabled=bool(args.source),
    )
    print(
        f"Fetched: {stats.fetched}, new: {stats.inserted}, "
        f"duplicates: {stats.duplicates}, failed sources: {stats.failed_sources}"
    )
    return 1 if stats.failed_sources else 0


if __name__ == "__main__":
    raise SystemExit(main())
