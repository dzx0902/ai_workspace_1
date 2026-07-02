from __future__ import annotations

from typing import Any

from .preprints import fetch_preprints, parse_item


def fetch_source(
    source: dict[str, Any],
    limit: int | None = None,
    timeout: int = 30,
):
    return fetch_preprints(source, "biorxiv", limit=limit, timeout=timeout)


__all__ = ["fetch_source", "parse_item"]
