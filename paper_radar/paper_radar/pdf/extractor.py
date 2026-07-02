from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import Paper
from ..storage import PaperStorage
from ..utils import load_yaml, resolve_project_path
from .downloader import safe_paper_name

LOGGER = logging.getLogger("paper_radar.pdf.extractor")


@dataclass(frozen=True)
class ExtractedPaper:
    title: str
    abstract: str
    section_headings: list[str]
    body: str
    page_count: int
    extractor: str


def _clean_page_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _section_headings(text: str) -> list[str]:
    headings: list[str] = []
    pattern = re.compile(
        r"^(?:(?:\d+(?:\.\d+)*)\s+)?"
        r"(?:abstract|introduction|background|related work|methods?|materials?"
        r"|experiments?|results?|discussion|conclusion|limitations?"
        r"|acknowledg(?:e)?ments?|references|appendix)\b.*$",
        re.IGNORECASE,
    )
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if 2 <= len(line) <= 100 and pattern.match(line) and line not in headings:
            headings.append(line)
    return headings


def _abstract_from_text(text: str, fallback: str) -> str:
    match = re.search(
        r"(?:^|\n)\s*abstract\s*(?:\n|[:.-])\s*(.+?)"
        r"(?=\n\s*(?:1\s+)?introduction\b|\n\s*keywords?\b)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return fallback


def _extract_with_pymupdf(path: Path) -> tuple[list[str], dict[str, str]]:
    import fitz

    pages: list[str] = []
    with fitz.open(str(path)) as document:
        metadata = document.metadata or {}
        for page in document:
            pages.append(_clean_page_text(page.get_text("text")))
    return pages, metadata


def _extract_with_pypdf(path: Path) -> tuple[list[str], dict[str, str]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [_clean_page_text(page.extract_text() or "") for page in reader.pages]
    metadata = reader.metadata or {}
    return pages, {"title": str(metadata.get("/Title") or "")}


def extract_pdf(path: Path, paper: Paper) -> ExtractedPaper:
    extractor = "pymupdf"
    try:
        pages, metadata = _extract_with_pymupdf(path)
    except Exception as primary_error:
        LOGGER.warning("PyMuPDF failed for %s, trying pypdf: %s", path, primary_error)
        extractor = "pypdf"
        pages, metadata = _extract_with_pypdf(path)
    nonempty = [page for page in pages if page]
    if not nonempty:
        raise ValueError("PDF did not contain extractable text")
    body = "\n\n".join(
        f"## Page {index}\n\n{page}"
        for index, page in enumerate(pages, 1)
        if page
    )
    first_line = next(
        (line.strip() for line in nonempty[0].splitlines() if line.strip()),
        "",
    )
    title = str(metadata.get("title") or "").strip() or first_line or paper.title
    return ExtractedPaper(
        title=title,
        abstract=_abstract_from_text("\n".join(nonempty), paper.summary),
        section_headings=_section_headings("\n".join(nonempty)),
        body=body,
        page_count=len(pages),
        extractor=extractor,
    )


def render_extracted_text(paper: Paper, extracted: ExtractedPaper) -> str:
    headings = "\n".join(f"- {value}" for value in extracted.section_headings) or "-"
    return f"""# {extracted.title}

## Metadata

- Paper ID: {paper.id}
- Source: {paper.source}
- URL: {paper.url}
- PDF: {paper.pdf_url}
- Pages: {extracted.page_count}
- Extractor: {extracted.extractor}

## Abstract

{extracted.abstract or "-"}

## Section Headings

{headings}

## Body

{extracted.body}
"""


class PDFExtractor:
    def __init__(
        self,
        storage: PaperStorage | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.storage = storage or PaperStorage()
        self.config = config or load_yaml("pdf.yaml")
        self.output_dir = resolve_project_path(self.config["extracted_text_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract(self, paper: Paper) -> Path | None:
        path = Path(paper.pdf_path).expanduser()
        if not path.exists():
            error = f"PDF file not found: {path}"
            self.storage.update_pdf_extract(paper.id, "extract_failed", error=error)
            LOGGER.error("%s: %s", paper.id, error)
            return None
        target = self.output_dir / f"{safe_paper_name(paper.id)}.md"
        try:
            extracted = extract_pdf(path, paper)
            target.write_text(render_extracted_text(paper, extracted), encoding="utf-8")
            self.storage.update_pdf_extract(paper.id, "extracted", str(target))
            LOGGER.info("%s: extracted PDF to %s", paper.id, target)
            return target
        except Exception as exc:
            self.storage.update_pdf_extract(paper.id, "extract_failed", error=str(exc))
            LOGGER.error("%s: PDF extraction failed: %s", paper.id, exc)
            return None

    def extract_candidates(self, limit: int | None = None) -> dict[str, int]:
        papers = self.storage.get_extract_candidates(limit)
        counts = {"processed": 0, "extracted": 0, "failed": 0}
        for paper in papers:
            counts["processed"] += 1
            if self.extract(paper):
                counts["extracted"] += 1
            else:
                counts["failed"] += 1
        return counts
