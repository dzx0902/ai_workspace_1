from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.pdf.downloader import PDFDownloader
from paper_radar.storage import PaperStorage
from paper_radar.utils import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Download PDFs for selected papers.")
    parser.add_argument("--paper-id")
    parser.add_argument("--date", help="Only use papers fetched on YYYY-MM-DD.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.date:
        try:
            date.fromisoformat(args.date)
        except ValueError:
            parser.error("--date must use YYYY-MM-DD")
    setup_logging(args.verbose)
    storage = PaperStorage()
    downloader = PDFDownloader(storage=storage)
    if args.paper_id:
        paper = storage.get_paper(args.paper_id)
        if paper is None:
            parser.error(f"paper not found: {args.paper_id}")
        path = downloader.download(paper)
        print(f"[download] {path}" if path else "[download] failed")
        return 0 if path else 1
    counts = downloader.download_candidates(limit=args.limit, date=args.date)
    print(
        f"[download] processed={counts['processed']} "
        f"downloaded={counts['downloaded']} failed={counts['failed']}"
    )
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
