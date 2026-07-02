from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..models import Paper
from . import arxiv_rss, biorxiv, huggingface, medrxiv, openreview, pubmed

SourceFetcher = Callable[[dict[str, Any], int | None, int], list[Paper]]

FETCHERS: dict[str, SourceFetcher] = {
    "arxiv_rss": arxiv_rss.fetch_source,
    "biorxiv": biorxiv.fetch_source,
    "medrxiv": medrxiv.fetch_source,
    "pubmed": pubmed.fetch_source,
    "openreview": openreview.fetch_source,
    "huggingface": huggingface.fetch_source,
}

SOURCE_ALIASES = {
    "arxiv": "arxiv_rss",
    "hf": "huggingface",
}


def normalize_source_type(value: str) -> str:
    normalized = value.strip().lower()
    return SOURCE_ALIASES.get(normalized, normalized)


def get_fetcher(source_type: str) -> SourceFetcher:
    normalized = normalize_source_type(source_type)
    try:
        return FETCHERS[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(FETCHERS))
        raise ValueError(
            f"Unsupported source type {source_type!r}; supported: {supported}"
        ) from exc
