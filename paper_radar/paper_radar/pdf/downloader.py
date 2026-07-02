from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import requests

from ..models import Paper
from ..sources.http import build_session
from ..storage import PaperStorage
from ..utils import load_yaml, resolve_project_path

LOGGER = logging.getLogger("paper_radar.pdf.downloader")


def safe_paper_name(paper_id: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", paper_id).strip("._")
    return value or "paper"


def resolve_pdf_url(paper: Paper) -> str:
    if paper.pdf_url:
        return paper.pdf_url
    if paper.source == "arxiv":
        external_id = paper.external_id or paper.id
        return f"https://arxiv.org/pdf/{external_id}.pdf"
    return ""


class PDFDownloader:
    def __init__(
        self,
        storage: PaperStorage | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.storage = storage or PaperStorage()
        self.config = config or load_yaml("pdf.yaml")
        self.download_dir = resolve_project_path(self.config["pdf_download_dir"])
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = int(self.config.get("download_timeout", 60))
        self.overwrite = bool(self.config.get("overwrite_existing_pdf", False))
        self.allowed_sources = {
            str(value).lower() for value in self.config.get("allowed_sources", [])
        }
        self.session = build_session()

    def download(self, paper: Paper) -> Path | None:
        if paper.source.lower() not in self.allowed_sources:
            error = f"Source {paper.source!r} is not allowed by config/pdf.yaml"
            self.storage.update_pdf_download(paper.id, "not_allowed", error=error)
            LOGGER.warning("%s: %s", paper.id, error)
            return None
        url = resolve_pdf_url(paper)
        if not url:
            error = "Paper does not have a PDF URL"
            self.storage.update_pdf_download(paper.id, "no_pdf_url", error=error)
            LOGGER.warning("%s: %s", paper.id, error)
            return None

        target = self.download_dir / f"{safe_paper_name(paper.id)}.pdf"
        if target.exists() and not self.overwrite:
            self.storage.update_pdf_download(paper.id, "downloaded", str(target))
            LOGGER.info("%s: PDF already exists at %s", paper.id, target)
            return target

        temporary: Path | None = None
        try:
            with self.session.get(
                url,
                timeout=self.timeout,
                stream=True,
                allow_redirects=True,
            ) as response:
                response.raise_for_status()
                fd, raw_path = tempfile.mkstemp(
                    prefix=f".{target.stem}.",
                    suffix=".pdf.part",
                    dir=target.parent,
                )
                temporary = Path(raw_path)
                with os.fdopen(fd, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            handle.write(chunk)
            with temporary.open("rb") as handle:
                signature = handle.read(5)
            if signature != b"%PDF-":
                raise ValueError("Downloaded response is not a PDF")
            os.replace(temporary, target)
            self.storage.update_pdf_download(paper.id, "downloaded", str(target))
            LOGGER.info("%s: downloaded PDF to %s", paper.id, target)
            return target
        except (requests.RequestException, OSError, ValueError) as exc:
            if temporary:
                temporary.unlink(missing_ok=True)
            self.storage.update_pdf_download(paper.id, "download_failed", error=str(exc))
            LOGGER.error("%s: PDF download failed: %s", paper.id, exc)
            return None

    def download_candidates(
        self,
        limit: int | None = None,
        date: str | None = None,
    ) -> dict[str, int]:
        configured_limit = int(self.config.get("max_pdf_per_run", 10))
        effective_limit = min(limit, configured_limit) if limit else configured_limit
        papers = self.storage.get_pdf_candidates(
            min_llm_score=float(self.config.get("min_llm_score_for_download", 8)),
            allowed_sources=self.allowed_sources,
            limit=effective_limit,
            date=date,
        )
        counts = {"processed": 0, "downloaded": 0, "failed": 0}
        for paper in papers:
            counts["processed"] += 1
            if self.download(paper):
                counts["downloaded"] += 1
            else:
                counts["failed"] += 1
        return counts
