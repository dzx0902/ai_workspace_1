from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.rag.query import PaperRAGQuery


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the Paper Radar knowledge base.")
    parser.add_argument("question")
    parser.add_argument("--llm", action="store_true")
    args = parser.parse_args()
    print(PaperRAGQuery().answer(args.question, use_llm=args.llm))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
