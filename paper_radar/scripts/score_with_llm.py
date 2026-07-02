from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.pipeline import score_all
from paper_radar.utils import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Score pending papers with an LLM.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    setup_logging(args.verbose)
    counts = score_all(limit=args.limit)
    print(
        f"Processed: {counts['processed']}, scored: {counts['scored']}, "
        f"failed: {counts['failed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
