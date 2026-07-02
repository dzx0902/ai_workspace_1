from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.pipeline import fetch_all
from paper_radar.utils import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch enabled arXiv RSS sources.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    stats = fetch_all()
    print(
        f"Fetched: {stats.fetched}, new: {stats.inserted}, "
        f"duplicates: {stats.duplicates}, failed sources: {stats.failed_sources}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
