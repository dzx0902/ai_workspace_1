from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.storage import PaperStorage
from paper_radar.utils import resolve_project_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a consistent SQLite backup.")
    parser.add_argument("--output-dir", default="data/backups")
    args = parser.parse_args()
    storage = PaperStorage()
    output_dir = resolve_project_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"papers-{datetime.now():%Y%m%d-%H%M%S}.db"
    with storage.connect() as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
