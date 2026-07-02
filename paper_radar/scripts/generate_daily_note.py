from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.pipeline import generate_note
from paper_radar.utils import setup_logging, today_string


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Paper Radar daily note.")
    parser.add_argument("--date", default=today_string(), help="YYYY-MM-DD")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    try:
        paths = generate_note(args.date, no_llm=args.no_llm)
    except ValueError:
        parser.error("--date must use YYYY-MM-DD")
    for path in paths:
        print(f"Daily note: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
