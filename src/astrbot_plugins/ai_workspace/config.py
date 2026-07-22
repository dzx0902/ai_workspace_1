from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

API_BASE = os.getenv("AI_WORKSPACE_API_BASE", "http://workspace-agent:8001").rstrip("/")
PAPER_API_BASE = os.getenv("PAPER_RADAR_API_BASE", API_BASE).rstrip("/")
PLANNER_API_BASE = os.getenv("PLANNER_API_BASE", "http://planner-agent:8000").rstrip("/")
FINANCE_API_BASE = os.getenv("FINANCE_API_BASE", "http://finance-agent:8020").rstrip("/")
SUBSCRIPTIONS_FILE = Path(
    os.getenv("PAPER_RADAR_SUBSCRIPTIONS", "/AstrBot/data/paper_radar_subscriptions.json")
)
PAPER_TIMEZONE = ZoneInfo(os.getenv("PAPER_RADAR_TIMEZONE", "Asia/Shanghai"))
PLATFORM_SCHEDULER_ENABLED = os.getenv("PLATFORM_SCHEDULER_ENABLED", "0") == "1"
