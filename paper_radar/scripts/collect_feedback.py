from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.feedback import collect_feedback
from paper_radar.storage import PaperStorage
from paper_radar.utils import resolve_project_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect feedback from Markdown notes.")
    parser.add_argument("--path", action="append")
    args = parser.parse_args()
    paths: list[Path] = []
    for raw in args.path or ["notes/daily"]:
        path = resolve_project_path(raw)
        paths.extend(path.rglob("*.md") if path.is_dir() else [path])
    counts = collect_feedback(paths, PaperStorage())
    print(
        f"[feedback] files={counts['files']} papers={counts['papers']} "
        f"missing={counts['missing']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
