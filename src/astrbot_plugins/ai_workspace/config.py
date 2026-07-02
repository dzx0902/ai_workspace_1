from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

API_BASE = os.getenv("AI_WORKSPACE_API_BASE", "http://host.docker.internal:8001").rstrip("/")
PAPER_API_BASE = os.getenv("PAPER_RADAR_API_BASE", API_BASE).rstrip("/")
SUBSCRIPTIONS_FILE = Path(
    os.getenv("PAPER_RADAR_SUBSCRIPTIONS", "/AstrBot/data/paper_radar_subscriptions.json")
)
PAPER_TIMEZONE = ZoneInfo(os.getenv("PAPER_RADAR_TIMEZONE", "Asia/Shanghai"))
