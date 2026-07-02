from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.paper_notes import PaperNoteService
from paper_radar.storage import PaperStorage
from paper_radar.utils import setup_logging, today_string


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate full-paper Markdown notes.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--paper-id")
    selection.add_argument("--date", help="YYYY-MM-DD; defaults to today.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    report_date = args.date or today_string()
    try:
        date.fromisoformat(report_date)
    except ValueError:
        parser.error("--date must use YYYY-MM-DD")
    setup_logging(args.verbose)
    storage = PaperStorage()
    service = PaperNoteService(storage=storage)
    if args.paper_id:
        paper = storage.get_paper(args.paper_id)
        if paper is None:
            parser.error(f"paper not found: {args.paper_id}")
        try:
            paths = service.summarize(paper)
        except Exception as exc:
            print(f"[summary] failed: {exc}")
            return 1
        for path in paths:
            print(f"[note] {path}")
        return 0
    counts = service.summarize_for_date(report_date, args.limit)
    print(
        f"[summary] processed={counts['processed']} "
        f"summarized={counts['summarized']} failed={counts['failed']}"
    )
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
