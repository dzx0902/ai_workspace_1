from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

from .llm.router import PaperLLMScorer
from .feedback import feedback_adjustment
from .markdown import render_daily_note, write_daily_note
from .models import FetchStats
from .scoring import decision_for_score, score_paper
from .sources.registry import get_fetcher, normalize_source_type
from .storage import PaperStorage
from .utils import load_yaml

LOGGER = logging.getLogger("paper_radar.pipeline")


def _estimated_cost(prompt_tokens: int, completion_tokens: int) -> float:
    input_rate = float(os.getenv("PAPER_RADAR_INPUT_COST_PER_M", "0"))
    output_rate = float(os.getenv("PAPER_RADAR_OUTPUT_COST_PER_M", "0"))
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000


def fetch_sources(
    storage: PaperStorage | None = None,
    source_type: str | None = None,
    limit: int | None = None,
    include_disabled: bool = False,
) -> FetchStats:
    storage = storage or PaperStorage()
    sources = load_yaml("sources.yaml").get("sources", [])
    selected_type = normalize_source_type(source_type) if source_type else None
    fetched = inserted = duplicates = failed = 0
    for source in sources:
        configured_type = normalize_source_type(str(source.get("type", "")))
        if selected_type and configured_type != selected_type:
            continue
        if not include_disabled and not source.get("enabled", False):
            continue
        try:
            fetcher = get_fetcher(configured_type)
            papers = fetcher(
                source,
                limit=limit,
                timeout=int(source.get("timeout", 30)),
            )
            source_inserted = sum(storage.upsert_paper(paper) for paper in papers)
            source_duplicates = len(papers) - source_inserted
            fetched += len(papers)
            inserted += source_inserted
            duplicates += source_duplicates
            LOGGER.info(
                "%s: fetched=%d inserted=%d duplicates=%d",
                source.get("name"),
                len(papers),
                source_inserted,
                source_duplicates,
            )
        except Exception as exc:
            failed += 1
            LOGGER.error("Source %s failed: %s", source.get("name"), exc)
    return FetchStats(fetched, inserted, duplicates, failed)


def fetch_all(storage: PaperStorage | None = None) -> FetchStats:
    return fetch_sources(storage=storage)


def filter_all(storage: PaperStorage | None = None) -> dict[str, int]:
    storage = storage or PaperStorage()
    keywords = load_yaml("keywords.yaml")
    scoring = load_yaml("scoring.yaml")
    threshold = int(scoring.get("llm_min_rule_score", 4))
    feedback_papers = storage.get_feedback_papers()
    counts = {"processed": 0, "llm_pending": 0, "rule_skipped": 0}
    for paper in storage.get_unfiltered():
        result = score_paper(paper, keywords, scoring)
        adjusted_score = result.score + feedback_adjustment(paper, feedback_papers)
        status = "llm_pending" if adjusted_score >= threshold else "rule_skipped"
        storage.update_rule_result(paper.id, adjusted_score, result.matches, status)
        counts["processed"] += 1
        counts[status] += 1
    return counts


def score_all(
    storage: PaperStorage | None = None,
    limit: int | None = None,
    scorer: PaperLLMScorer | None = None,
    report_date: str | None = None,
) -> dict[str, int]:
    storage = storage or PaperStorage()
    papers = storage.get_llm_pending(limit, date=report_date)
    scoring_config = load_yaml("scoring.yaml")
    counts = {"processed": 0, "scored": 0, "failed": 0}
    try:
        scorer = scorer or PaperLLMScorer()
    except Exception as exc:
        LOGGER.error("LLM client initialization failed: %s", exc)
        for paper in papers:
            storage.mark_llm_failed(paper.id, str(exc))
            counts["processed"] += 1
            counts["failed"] += 1
        return counts
    for paper in papers:
        counts["processed"] += 1
        try:
            result = scorer.score(paper)
            result["decision"] = decision_for_score(result["relevance_score"], scoring_config)
            storage.update_llm_result(paper.id, result)
            usage = getattr(scorer, "last_usage", {})
            prompt_tokens = int(usage.get("prompt_tokens", 0))
            completion_tokens = int(usage.get("completion_tokens", 0))
            storage.record_llm_usage(
                paper.id,
                "screening",
                scorer.config.provider,
                scorer.config.model,
                prompt_tokens,
                completion_tokens,
                _estimated_cost(prompt_tokens, completion_tokens),
            )
            counts["scored"] += 1
        except Exception as exc:
            LOGGER.error("LLM scoring failed for %s: %s", paper.id, exc)
            storage.mark_llm_failed(paper.id, str(exc))
            counts["failed"] += 1
    return counts


def generate_note(
    report_date: str,
    storage: PaperStorage | None = None,
    no_llm: bool = False,
) -> list[Path]:
    date.fromisoformat(report_date)
    storage = storage or PaperStorage()
    papers = storage.get_candidates_for_date(report_date)
    content = render_daily_note(report_date, papers, no_llm=no_llm)
    return write_daily_note(report_date, content)


def run_daily(report_date: str, limit_llm: int | None, no_llm: bool) -> list[Path]:
    date.fromisoformat(report_date)
    storage = PaperStorage()
    fetched = fetch_all(storage)
    LOGGER.info(
        "fetch: fetched=%d new=%d duplicates=%d failed_sources=%d",
        fetched.fetched,
        fetched.inserted,
        fetched.duplicates,
        fetched.failed_sources,
    )
    filtered = filter_all(storage)
    LOGGER.info("filter: %s", filtered)
    if not no_llm:
        LOGGER.info(
            "llm: %s",
            score_all(storage, limit=limit_llm, report_date=report_date),
        )
    return generate_note(report_date, storage=storage, no_llm=no_llm)
