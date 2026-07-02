from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.pdf.extractor import PDFExtractor
from paper_radar.storage import PaperStorage
from paper_radar.utils import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from downloaded PDFs.")
    parser.add_argument("--paper-id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    setup_logging(args.verbose)
    storage = PaperStorage()
    extractor = PDFExtractor(storage=storage)
    if args.paper_id:
        paper = storage.get_paper(args.paper_id)
        if paper is None:
            parser.error(f"paper not found: {args.paper_id}")
        path = extractor.extract(paper)
        print(f"[extract] {path}" if path else "[extract] failed")
        return 0 if path else 1
    counts = extractor.extract_candidates(args.limit)
    print(
        f"[extract] processed={counts['processed']} "
        f"extracted={counts['extracted']} failed={counts['failed']}"
    )
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
