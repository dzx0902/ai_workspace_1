from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_script(name: str, *args: str) -> bool:
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / name), *args]
    print(f"[automation] {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if completed.returncode:
        print(
            f"[automation] {name} failed with code {completed.returncode}; continuing",
            file=sys.stderr,
        )
        return False
    return True


def run_daily(report_date: str, limit_llm: int, summarize_limit: int) -> int:
    results = [
        run_script("backup_database.py"),
        run_script(
            "collect_feedback.py",
            "--path",
            "/mnt/f/ObsidianVault/AI/PaperRadar",
        ),
        run_script(
            "run_daily.py",
            "--date",
            report_date,
            "--limit-llm",
            str(limit_llm),
        ),
        run_script(
            "download_pdfs.py",
            "--date",
            report_date,
            "--limit",
            str(summarize_limit),
        ),
        run_script("extract_pdfs.py", "--limit", str(summarize_limit)),
        run_script(
            "summarize_paper.py",
            "--date",
            report_date,
            "--limit",
            str(summarize_limit),
        ),
        run_script("generate_topic_note.py", "--all", "--days", "90"),
        run_script("ingest_notes_to_chroma.py"),
    ]
    return 0 if all(results) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run scheduled Paper Radar workflows.")
    parser.add_argument(
        "workflow",
        choices=("daily", "weekly", "monthly", "maintenance"),
    )
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--limit-llm", type=int, default=20)
    parser.add_argument("--summarize-limit", type=int, default=3)
    args = parser.parse_args()

    if args.workflow == "daily":
        return run_daily(args.date, args.limit_llm, args.summarize_limit)
    if args.workflow == "weekly":
        ok = run_script("generate_weekly_review.py", "--date", args.date)
        return 0 if run_script("ingest_notes_to_chroma.py") and ok else 1
    if args.workflow == "monthly":
        ok = run_script("generate_monthly_review.py", "--date", args.date)
        return 0 if run_script("ingest_notes_to_chroma.py") and ok else 1
    results = [
        run_script("backup_database.py"),
        run_script(
            "collect_feedback.py",
            "--path",
            "/mnt/f/ObsidianVault/AI/PaperRadar",
        ),
        run_script("ingest_notes_to_chroma.py"),
    ]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
