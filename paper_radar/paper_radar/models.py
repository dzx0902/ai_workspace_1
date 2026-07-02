from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Paper:
    id: str
    title: str
    external_id: str = ""
    authors: list[str] = field(default_factory=list)
    summary: str = ""
    source: str = "arxiv"
    source_category: str = ""
    url: str = ""
    pdf_url: str = ""
    published: str = ""
    fetched_at: str = ""
    rule_score: int | None = None
    matched_keywords: list[dict[str, Any]] = field(default_factory=list)
    llm_score: float | None = None
    llm_category: list[str] = field(default_factory=list)
    llm_decision: str = ""
    llm_reason: str = ""
    note_priority: str = ""
    status: str = "fetched"
    llm_error: str = ""
    pdf_path: str = ""
    pdf_download_status: str = ""
    pdf_download_error: str = ""
    extracted_text_path: str = ""
    pdf_extract_status: str = ""
    pdf_extract_error: str = ""
    paper_note_path: str = ""
    full_summary_status: str = ""
    full_summary_error: str = ""
    feedback_relevant: int = 0
    feedback_not_relevant: int = 0
    feedback_read_later: int = 0
    feedback_related_work: int = 0
    feedback_summarize: int = 0


@dataclass(frozen=True)
class FetchStats:
    fetched: int = 0
    inserted: int = 0
    duplicates: int = 0
    failed_sources: int = 0
