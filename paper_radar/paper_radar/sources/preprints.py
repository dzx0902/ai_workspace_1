from __future__ import annotations

import logging
from typing import Any

import requests

from ..models import Paper
from ..utils import clean_text, now_iso
from .http import build_session

LOGGER = logging.getLogger("paper_radar.sources.preprints")
API_ROOT = "https://api.biorxiv.org/details"


def parse_item(item: dict[str, Any], server: str, category: str, fetched_at: str) -> Paper:
    doi = clean_text(item.get("doi"))
    if not doi:
        raise ValueError("Preprint response did not contain a DOI")
    version = clean_text(item.get("version")) or "1"
    source = server.lower()
    base_url = f"https://www.{source}.org/content/{doi}v{version}"
    return Paper(
        id=f"{source}:{doi}",
        external_id=doi,
        title=clean_text(item.get("title")) or "(untitled)",
        authors=[
            value.strip()
            for value in clean_text(item.get("authors")).split(";")
            if value.strip()
        ],
        summary=clean_text(item.get("abstract")),
        source=source,
        source_category=clean_text(item.get("category")) or category,
        url=base_url,
        pdf_url=f"{base_url}.full.pdf",
        published=clean_text(item.get("date")),
        fetched_at=fetched_at,
    )


def fetch_preprints(
    source: dict[str, Any],
    server: str,
    limit: int | None = None,
    timeout: int = 30,
) -> list[Paper]:
    recent_days = int(source.get("recent_days", 7))
    category = str(source.get("category", ""))
    subject_filter = clean_text(source.get("subject_filter"))
    base_url = str(source.get("url") or API_ROOT).rstrip("/")
    cursor = 0
    papers: list[Paper] = []
    fetched_at = now_iso()
    session = build_session()

    while limit is None or len(papers) < limit:
        url = f"{base_url}/{server}/{recent_days}d/{cursor}/json"
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RuntimeError(f"Failed to fetch {server} API {url}: {exc}") from exc

        items = payload.get("collection") or []
        if not isinstance(items, list):
            raise RuntimeError(f"Unexpected {server} API response: collection is not a list")
        for item in items:
            try:
                paper = parse_item(item, server, category, fetched_at)
            except (TypeError, ValueError):
                LOGGER.exception("Skipping malformed %s record", server)
                continue
            if (
                subject_filter
                and subject_filter.casefold() != paper.source_category.casefold()
            ):
                continue
            papers.append(paper)
            if limit is not None and len(papers) >= limit:
                break

        messages = payload.get("messages") or []
        total = 0
        if messages and isinstance(messages[0], dict):
            try:
                total = int(messages[0].get("total") or 0)
            except (TypeError, ValueError):
                total = 0
        cursor += len(items)
        if not items or (total and cursor >= total):
            break

    return papers
