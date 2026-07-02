from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.topics import TopicService
from paper_radar.utils import today_string


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a weekly paper review.")
    parser.add_argument("--date", default=today_string())
    args = parser.parse_args()
    print(TopicService().generate_review(date.fromisoformat(args.date), "weekly"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
