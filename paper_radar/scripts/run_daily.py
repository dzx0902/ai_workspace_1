from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from paper_radar.storage import PaperStorage
from paper_radar.pipeline import fetch_all, filter_all, generate_note, score_all
from paper_radar.markdown import render_daily_note
from paper_radar.utils import setup_logging, today_string


def run_daily(
    report_date: str,
    limit_llm: int | None,
    no_llm: bool,
    dry_run: bool = False,
) -> list[Path]:
    date.fromisoformat(report_date)
    temporary = tempfile.TemporaryDirectory() if dry_run else None
    storage = PaperStorage(Path(temporary.name) / "papers.db") if temporary else PaperStorage()

    fetched = fetch_all(storage)
    print(
        f"[fetch] fetched={fetched.fetched} new={fetched.inserted} "
        f"duplicates={fetched.duplicates} failed_sources={fetched.failed_sources}"
    )

    filtered = filter_all(storage)
    print(
        f"[filter] processed={filtered['processed']} "
        f"pending={filtered['llm_pending']} skipped={filtered['rule_skipped']}"
    )

    if no_llm:
        print("[llm] skipped by --no-llm")
    else:
        scored = score_all(storage, limit=limit_llm, report_date=report_date)
        print(
            f"[llm] processed={scored['processed']} "
            f"scored={scored['scored']} failed={scored['failed']}"
        )

    if dry_run:
        papers = storage.get_candidates_for_date(report_date)
        render_daily_note(report_date, papers, no_llm=no_llm)
        print(f"[dry-run] would generate note with {len(papers)} papers")
        paths = []
    else:
        paths = generate_note(report_date, storage=storage, no_llm=no_llm)
    for path in paths:
        print(f"[note] {path}")
    if not dry_run:
        usage = storage.llm_usage_summary(report_date)
        print(
            f"[cost] calls={usage['calls']} prompt_tokens={usage['prompt_tokens']} "
            f"completion_tokens={usage['completion_tokens']} "
            f"estimated_cost={usage['estimated_cost']:.6f}"
        )
    if temporary:
        temporary.cleanup()
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete Paper Radar pipeline.")
    parser.add_argument("--limit-llm", type=int, default=50)
    parser.add_argument("--date", default=today_string(), help="YYYY-MM-DD")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if args.limit_llm < 1:
        parser.error("--limit-llm must be at least 1")
    setup_logging(args.verbose)
    try:
        run_daily(args.date, args.limit_llm, args.no_llm, args.dry_run)
    except ValueError:
        parser.error("--date must use YYYY-MM-DD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
