from __future__ import annotations

import logging
import os
from typing import Any

import requests

from ..models import Paper
from ..utils import clean_text, load_environment, now_iso
from .http import build_session

LOGGER = logging.getLogger("paper_radar.sources.openreview")
API_URL = "https://api2.openreview.net/notes"
LOGIN_URL = "https://api2.openreview.net/login"
MAX_TOKEN_EXPIRES_IN = 7 * 24 * 60 * 60


def _content_value(content: dict[str, Any], key: str) -> Any:
    value = content.get(key, "")
    return value.get("value", "") if isinstance(value, dict) else value


def _auth_token() -> str:
    load_environment()
    token = (
        os.getenv("PAPER_RADAR_OPENREVIEW_TOKEN")
        or os.getenv("OPENREVIEW_TOKEN")
        or ""
    ).strip()
    return token.removeprefix("Bearer ").strip()


def _login_token(session: requests.Session, timeout: int) -> str:
    load_environment()
    username = (
        os.getenv("PAPER_RADAR_OPENREVIEW_USERNAME")
        or os.getenv("OPENREVIEW_USERNAME")
        or ""
    ).strip()
    password = (
        os.getenv("PAPER_RADAR_OPENREVIEW_PASSWORD")
        or os.getenv("OPENREVIEW_PASSWORD")
        or ""
    ).strip()
    if not username and not password:
        return ""
    if not username or not password:
        raise RuntimeError(
            "OpenReview username and password must be configured together. "
            "Set PAPER_RADAR_OPENREVIEW_USERNAME and "
            "PAPER_RADAR_OPENREVIEW_PASSWORD, or provide PAPER_RADAR_OPENREVIEW_TOKEN."
        )

    expires_in = int(
        os.getenv("PAPER_RADAR_OPENREVIEW_TOKEN_EXPIRES_IN", str(MAX_TOKEN_EXPIRES_IN))
    )
    expires_in = max(1, min(expires_in, MAX_TOKEN_EXPIRES_IN))
    response = session.post(
        LOGIN_URL,
        json={"id": username, "password": password, "expiresIn": expires_in},
        timeout=timeout,
    )
    _raise_openreview_error(response)
    token = clean_text(response.json().get("token"))
    if not token:
        raise RuntimeError("OpenReview login response did not include a token.")
    return token.removeprefix("Bearer ").strip()


def _raise_openreview_error(response: requests.Response) -> None:
    try:
        payload = response.json()
    except ValueError:
        response.raise_for_status()
        return
    name = clean_text(payload.get("name"))
    message = clean_text(payload.get("message"))
    if response.status_code == 403 and name == "ChallengeRequiredError":
        raise RuntimeError(
            "OpenReview requires challenge verification for anonymous /notes API "
            "requests. Set PAPER_RADAR_OPENREVIEW_USERNAME and "
            "PAPER_RADAR_OPENREVIEW_PASSWORD for automatic login, provide a valid "
            "PAPER_RADAR_OPENREVIEW_TOKEN, or disable the OpenReview source."
        )
    response.raise_for_status()
    if message:
        raise RuntimeError(f"{name or 'OpenReviewError'}: {message}")


def fetch_source(
    source: dict[str, Any],
    limit: int | None = None,
    timeout: int = 30,
) -> list[Paper]:
    venue = clean_text(source.get("venue"))
    invitation = clean_text(source.get("invitation"))
    query = clean_text(source.get("query"))
    effective_limit = limit if limit is not None else int(source.get("max_results", 50))
    params: dict[str, Any] = {"limit": effective_limit, "details": "replyCount"}
    if invitation:
        params["invitation"] = invitation
    elif venue:
        params["content.venueid"] = venue
    elif query:
        params["term"] = query
    else:
        raise ValueError("OpenReview source requires invitation, venue, or query")

    try:
        session = build_session()
        token = _auth_token() or _login_token(session, timeout)
        if token:
            session.headers["Authorization"] = f"Bearer {token}"
        response = session.get(
            str(source.get("url") or API_URL),
            params=params,
            timeout=timeout,
        )
        _raise_openreview_error(response)
        notes = response.json().get("notes", [])
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"OpenReview fetch failed: {exc}") from exc

    fetched_at = now_iso()
    papers = []
    for note in notes:
        content = note.get("content") or {}
        title = clean_text(_content_value(content, "title"))
        if not title:
            continue
        note_id = clean_text(note.get("id") or note.get("forum"))
        authors = _content_value(content, "authors")
        if not isinstance(authors, list):
            authors = [clean_text(authors)] if authors else []
        paper_venue = clean_text(_content_value(content, "venue")) or venue
        papers.append(
            Paper(
                id=f"openreview:{note_id}",
                external_id=note_id,
                title=title,
                authors=[clean_text(author) for author in authors if clean_text(author)],
                summary=clean_text(_content_value(content, "abstract")),
                source="openreview",
                source_category=paper_venue or str(source.get("category", "")),
                url=f"https://openreview.net/forum?id={note_id}",
                pdf_url=f"https://openreview.net/pdf?id={note_id}",
                published="",
                fetched_at=fetched_at,
            )
        )
    if query:
        needle = query.casefold()
        papers = [
            paper
            for paper in papers
            if needle in f"{paper.title} {paper.summary}".casefold()
        ]
    return papers[:effective_limit]
