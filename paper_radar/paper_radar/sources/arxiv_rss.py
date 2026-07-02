from __future__ import annotations

import logging
import re
from time import struct_time
from typing import Any

import feedparser
import requests

from ..models import Paper
from ..utils import clean_text, now_iso
from .http import build_session

LOGGER = logging.getLogger("paper_radar.sources.arxiv")
_ARXIV_ID = re.compile(
    r"(?:abs|pdf)/(?P<id>(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7}))(?:v\d+)?",
    re.IGNORECASE,
)


def extract_arxiv_id(url: str) -> str:
    match = _ARXIV_ID.search(url or "")
    if match:
        return match.group("id")
    value = (url or "").rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"(?:v\d+)?(?:\.pdf)?$", "", value)


def _published_value(entry: Any) -> str:
    parsed: struct_time | None = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return (
            f"{parsed.tm_year:04d}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"
            f"T{parsed.tm_hour:02d}:{parsed.tm_min:02d}:{parsed.tm_sec:02d}+00:00"
        )
    return clean_text(entry.get("published") or entry.get("updated"))


def _authors(entry: Any) -> list[str]:
    values = entry.get("authors") or []
    names = [clean_text(author.get("name")) for author in values if author.get("name")]
    if names:
        return names
    raw = clean_text(entry.get("author"))
    return [name.strip() for name in re.split(r",| and ", raw) if name.strip()]


def parse_entry(entry: Any, category: str, fetched_at: str | None = None) -> Paper:
    raw_url = clean_text(entry.get("link") or entry.get("id"))
    arxiv_id = extract_arxiv_id(raw_url)
    if not arxiv_id:
        raise ValueError(f"Could not determine arXiv id from entry URL: {raw_url!r}")
    url = f"https://arxiv.org/abs/{arxiv_id}"
    return Paper(
        id=arxiv_id,
        title=clean_text(entry.get("title")) or "(untitled)",
        external_id=arxiv_id,
        authors=_authors(entry),
        summary=clean_text(entry.get("summary") or entry.get("description")),
        source="arxiv",
        source_category=category,
        url=url,
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
        published=_published_value(entry),
        fetched_at=fetched_at or now_iso(),
    )


def fetch_source(
    source: dict[str, Any],
    limit: int | None = None,
    timeout: int = 30,
) -> list[Paper]:
    url = str(source["url"])
    category = str(source.get("category", ""))
    try:
        response = build_session().get(url, timeout=timeout)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except (requests.RequestException, OSError) as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc
    if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
        raise RuntimeError(f"Invalid RSS response from {url}: {feed.bozo_exception}")

    fetched_at = now_iso()
    papers: list[Paper] = []
    entries = getattr(feed, "entries", [])
    if limit is not None:
        entries = entries[:limit]
    for entry in entries:
        try:
            papers.append(parse_entry(entry, category, fetched_at=fetched_at))
        except Exception:
            LOGGER.exception("Skipping malformed entry from %s", url)
    return papers
