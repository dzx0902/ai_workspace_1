from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.rag.ingest import PaperRAGIngestor
from paper_radar.utils import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest Paper Radar notes into Chroma.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)
    counts = PaperRAGIngestor().ingest_all(force=args.force)
    print(
        f"[rag] files={counts['files']} chunks={counts['chunks']} "
        f"skipped={counts['skipped']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
