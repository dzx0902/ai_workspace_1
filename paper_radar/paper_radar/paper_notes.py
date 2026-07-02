from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from .llm.fullpaper import FullPaperSummarizer
from .markdown import _atomic_write
from .models import Paper
from .pdf.downloader import safe_paper_name
from .storage import PaperStorage
from .utils import load_yaml, resolve_project_path

LOGGER = logging.getLogger("paper_radar.paper_notes")


def _list_markdown(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) or "- 未报告"


def render_paper_note(paper: Paper, summary: dict[str, Any]) -> str:
    authors = ", ".join(paper.authors) or "-"
    tags = " ".join(
        f"#{tag.strip().replace(' ', '-').replace('_', '-')}"
        for tag in summary["tags"]
    ) or "-"
    score = f"{paper.llm_score:g}/10" if paper.llm_score is not None else "-"
    return f"""# {paper.title}

## Metadata

* Title: {paper.title}
* Authors: {authors}
* Source: {paper.source}
* Published: {paper.published or "-"}
* URL: {paper.url or "-"}
* PDF: {paper.pdf_url or paper.pdf_path or "-"}
* Tags: {tags}
* LLM Score: {score}
* Decision: {paper.llm_decision or "-"}

## 一句话总结

{summary["sentence_summary"]}

## 研究问题

{summary["research_question"]}

## 核心贡献

{_list_markdown(summary["core_contributions"])}

## 方法概述

{summary["method_overview"]}

## 数据集与实验设置

{summary["datasets_experiments"]}

## 关键结果

{summary["key_results"]}

## 与我研究方向的关系

{summary["research_relevance"]}

## 可借鉴之处

{_list_markdown(summary["transferable_ideas"])}

## 局限与疑问

{summary["limitations_questions"]}

## 后续动作

* [ ] 精读全文
* [ ] 查代码
* [ ] 加入 related work
* [ ] 查作者其他工作
* [ ] 复现实验或方法迁移
"""


def write_paper_note(
    paper: Paper,
    content: str,
    config: dict[str, Any],
) -> list[Path]:
    filename = f"{safe_paper_name(paper.id)}.md"
    targets = [
        resolve_project_path(config.get("paper_notes_dir", "notes/papers")) / filename
    ]
    obsidian = config.get("obsidian_paper_notes_dir")
    if obsidian:
        targets.append(resolve_project_path(obsidian) / filename)
    written = []
    for target in dict.fromkeys(targets):
        try:
            _atomic_write(target, content)
            written.append(target)
        except OSError as exc:
            LOGGER.error("Could not write paper note to %s: %s", target, exc)
    if not written:
        raise OSError("Paper note could not be written to any configured output")
    return written


class PaperNoteService:
    def __init__(
        self,
        storage: PaperStorage | None = None,
        config: dict[str, Any] | None = None,
        summarizer: FullPaperSummarizer | None = None,
    ):
        self.storage = storage or PaperStorage()
        self.config = config or load_yaml("pdf.yaml")
        self.summarizer = summarizer

    def summarize(self, paper: Paper) -> list[Path]:
        extracted_path = Path(paper.extracted_text_path).expanduser()
        if not extracted_path.exists():
            error = f"Extracted text not found: {extracted_path}"
            self.storage.update_full_summary(paper.id, "summary_failed", error=error)
            raise FileNotFoundError(error)
        max_chars = int(self.config.get("max_fulltext_chars_for_llm", 120000))
        fulltext = extracted_path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
        try:
            summarizer = self.summarizer or FullPaperSummarizer()
            summary = summarizer.summarize(paper, fulltext)
            paths = write_paper_note(paper, render_paper_note(paper, summary), self.config)
            usage = getattr(summarizer, "last_usage", {})
            llm_config = getattr(summarizer, "config", None)
            if llm_config:
                self.storage.record_llm_usage(
                    paper.id,
                    "fullpaper",
                    llm_config.provider,
                    llm_config.model,
                    int(usage.get("prompt_tokens", 0)),
                    int(usage.get("completion_tokens", 0)),
                    (
                        int(usage.get("prompt_tokens", 0))
                        * float(os.getenv("PAPER_RADAR_STRONG_INPUT_COST_PER_M", "0"))
                        + int(usage.get("completion_tokens", 0))
                        * float(os.getenv("PAPER_RADAR_STRONG_OUTPUT_COST_PER_M", "0"))
                    )
                    / 1_000_000,
                )
            self.storage.update_full_summary(paper.id, "summarized", str(paths[0]))
            return paths
        except Exception as exc:
            self.storage.update_full_summary(
                paper.id,
                "summary_failed",
                error=str(exc),
            )
            raise

    def summarize_for_date(self, date: str, limit: int | None = None) -> dict[str, int]:
        papers = self.storage.get_summary_candidates(date, limit)
        counts = {"processed": 0, "summarized": 0, "failed": 0}
        for paper in papers:
            counts["processed"] += 1
            try:
                self.summarize(paper)
                counts["summarized"] += 1
            except Exception as exc:
                LOGGER.error("%s: full-paper summary failed: %s", paper.id, exc)
                counts["failed"] += 1
        return counts
