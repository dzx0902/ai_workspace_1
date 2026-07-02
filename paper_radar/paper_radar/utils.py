from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
DB_PATH = DATA_DIR / "papers.db"


def project_timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("PAPER_RADAR_TIMEZONE", "Asia/Shanghai"))


def load_environment() -> None:
    load_dotenv(PROJECT_ROOT.parent / ".env")
    load_dotenv(PROJECT_ROOT / ".env", override=True)


def load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuration root must be a mapping: {path}")
    return data


def setup_logging(verbose: bool = False) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    log_path = LOG_DIR / f"paper_radar-{today_string()}.log"
    try:
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
    except OSError:
        fallback_path = LOG_DIR / f"paper_radar-{today_string()}-uid{os.getuid()}.log"
        file_handler = logging.FileHandler(fallback_path, encoding="utf-8")
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        file_handler,
    ]
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("paper_radar")


def now_iso() -> str:
    return datetime.now(project_timezone()).isoformat(timespec="seconds")


def today_string() -> str:
    return datetime.now(project_timezone()).date().isoformat()


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", unescape(str(value)))
    return re.sub(r"\s+", " ", text).strip()


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()
