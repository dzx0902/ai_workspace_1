from __future__ import annotations

import logging
import re
from typing import Any

import feedparser
import requests

from ..models import Paper
from ..utils import clean_text, now_iso
from .http import build_session

LOGGER = logging.getLogger("paper_radar.sources.huggingface")
DEFAULT_RSS_URL = "https://huggingface.co/papers/rss"


def fetch_source(
    source: dict[str, Any],
    limit: int | None = None,
    timeout: int = 30,
) -> list[Paper]:
    url = str(source.get("url") or DEFAULT_RSS_URL)
    try:
        response = build_session().get(url, timeout=timeout)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.RequestException as exc:
        raise RuntimeError(f"Hugging Face Papers fetch failed: {exc}") from exc
    if getattr(feed, "bozo", False) and not getattr(feed, "entries", []):
        raise RuntimeError(f"Hugging Face Papers RSS parse failed: {feed.bozo_exception}")

    fetched_at = now_iso()
    papers = []
    entries = getattr(feed, "entries", [])
    if limit is not None:
        entries = entries[:limit]
    for entry in entries:
        paper_url = clean_text(entry.get("link") or entry.get("id"))
        external_id = paper_url.rstrip("/").rsplit("/", 1)[-1]
        if not external_id:
            LOGGER.warning("Skipping Hugging Face entry without an id: %s", paper_url)
            continue
        authors = [
            clean_text(author.get("name"))
            for author in (entry.get("authors") or [])
            if clean_text(author.get("name"))
        ]
        if not authors:
            raw_author = clean_text(entry.get("author"))
            authors = [
                value.strip()
                for value in re.split(r",| and ", raw_author)
                if value.strip()
            ]
        papers.append(
            Paper(
                id=f"huggingface:{external_id}",
                external_id=external_id,
                title=clean_text(entry.get("title")) or "(untitled)",
                authors=authors,
                summary=clean_text(entry.get("summary") or entry.get("description")),
                source="huggingface",
                source_category=str(source.get("category", "daily-papers")),
                url=paper_url,
                pdf_url="",
                published=clean_text(entry.get("published") or entry.get("updated")),
                fetched_at=fetched_at,
            )
        )
    return papers
