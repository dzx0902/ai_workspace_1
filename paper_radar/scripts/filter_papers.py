from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.pipeline import filter_all
from paper_radar.utils import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply keyword rules to fetched papers.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    counts = filter_all()
    print(
        f"Processed: {counts['processed']}, pending LLM: {counts['llm_pending']}, "
        f"rule skipped: {counts['rule_skipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
