from __future__ import annotations

import json
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = PROJECT_ROOT / "data" / "scheduler_state.json"
TIMEZONE = ZoneInfo("Asia/Shanghai")
STOP = False


@dataclass(frozen=True)
class Job:
    name: str
    workflow: str
    hour: int
    minute: int
    weekday: int | None = None
    monthday: int | None = None

    def due_date(self, now: datetime) -> str | None:
        if self.weekday is not None and now.weekday() != self.weekday:
            return None
        if self.monthday is not None and now.day != self.monthday:
            return None
        if (now.hour, now.minute) < (self.hour, self.minute):
            return None
        return now.date().isoformat()


JOBS = (
    Job("daily", "daily", 7, 30),
    Job("maintenance", "maintenance", 12, 30),
    Job("weekly", "weekly", 18, 0, weekday=6),
    Job("monthly", "monthly", 18, 30, monthday=1),
)


def load_state() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    STATE_PATH.chmod(0o644)


def run_job(job: Job, report_date: str) -> bool:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_automation.py"),
        job.workflow,
        "--date",
        report_date,
    ]
    print(f"[scheduler] starting {job.name}: {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    print(
        f"[scheduler] finished {job.name}: code={completed.returncode}",
        flush=True,
    )
    return completed.returncode == 0


def mark_past_jobs_on_first_start(state: dict[str, str], now: datetime) -> None:
    if state:
        return
    for job in JOBS:
        due = job.due_date(now)
        if due:
            state[job.name] = due
    save_state(state)


def stop_handler(signum, frame) -> None:
    global STOP
    STOP = True


def main() -> int:
    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)
    state = load_state()
    now = datetime.now(TIMEZONE)
    mark_past_jobs_on_first_start(state, now)
    print(
        f"[scheduler] ready timezone={TIMEZONE.key} state={state}",
        flush=True,
    )
    while not STOP:
        now = datetime.now(TIMEZONE)
        for job in JOBS:
            due = job.due_date(now)
            if due and state.get(job.name) != due:
                if run_job(job, due):
                    state[job.name] = due
                    save_state(state)
        time.sleep(30)
    print("[scheduler] stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
