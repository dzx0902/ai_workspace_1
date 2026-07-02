from __future__ import annotations

import logging
import os
import tempfile
from datetime import date as date_type
from pathlib import Path
from typing import Iterable

from .models import Paper
from .utils import load_yaml, resolve_project_path

LOGGER = logging.getLogger("paper_radar.markdown")


def _match_text(paper: Paper) -> str:
    values = []
    for item in paper.matched_keywords:
        label = f"{item.get('topic')}: {item.get('keyword')}"
        if label not in values:
            values.append(label)
    return ", ".join(values) or "-"


def _tags(paper: Paper) -> str:
    categories = paper.llm_category or [
        str(item.get("topic")) for item in paper.matched_keywords if item.get("topic")
    ]
    return " ".join(f"#{value.replace('_', '-')}" for value in dict.fromkeys(categories)) or "-"


def _paper_block(index: int, paper: Paper, no_llm: bool) -> str:
    relevance = (
        f"{paper.llm_score:g}/10"
        if paper.llm_score is not None
        else f"rule score {paper.rule_score or 0}"
    )
    reason = paper.llm_reason or (
        "未执行 LLM 评分，按关键词规则分归类。" if no_llm else paper.llm_error or "-"
    )
    judgment = paper.llm_decision or ("规则候选" if paper.status == "llm_pending" else "规则跳过")
    authors = ", ".join(paper.authors) or "-"
    return f"""### {index}. {paper.title}
<!-- paper_id: {paper.id} -->
- Authors: {authors}
- Source: {paper.source}
- Category: {paper.source_category or "-"}
- Published: {paper.published or "-"}
- URL: {paper.url}
- PDF: {paper.pdf_url}
- Relevance: {relevance}
- Tags: {_tags(paper)}
- Matched Keywords: {_match_text(paper)}
- Reason: {reason}
- 一句话判断: {judgment}

反馈：
- [{"x" if paper.feedback_relevant else " "}] relevant
- [{"x" if paper.feedback_not_relevant else " "}] not relevant
- [{"x" if paper.feedback_read_later else " "}] read later
- [{"x" if paper.feedback_related_work else " "}] add to related work
- [{"x" if paper.feedback_summarize else " "}] summarize full paper
"""


def _fallback_decision(paper: Paper, threshold: int) -> str:
    if paper.status == "rule_skipped":
        return "skip"
    return "read" if (paper.rule_score or 0) >= threshold * 2 else "skim"


def render_daily_note(
    report_date: str,
    papers: list[Paper],
    no_llm: bool = False,
    scoring_config: dict | None = None,
) -> str:
    scoring_config = scoring_config or load_yaml("scoring.yaml")
    threshold = int(scoring_config.get("llm_min_rule_score", 4))
    groups: dict[str, list[Paper]] = {
        "read": [],
        "skim": [],
        "ai": [],
        "brain": [],
        "skip": [],
    }
    for paper in papers:
        decision = paper.llm_decision or _fallback_decision(paper, threshold)
        if decision == "read":
            groups["read"].append(paper)
        elif decision == "skim":
            groups["skim"].append(paper)
        elif set(paper.llm_category) & {"ai_core", "ai_sota"}:
            groups["ai"].append(paper)
        elif set(paper.llm_category) & {"brain_signal", "brain_decoding", "neuroscience"}:
            groups["brain"].append(paper)
        else:
            groups["skip"].append(paper)

    lines = [
        f"# Paper Radar - {report_date}",
        "",
        "## 今日概览",
        f"- 抓取论文数：{len(papers)}",
        f"- 初筛通过：{sum(p.status != 'rule_skipped' for p in papers)}",
        f"- LLM 推荐精读：{sum(p.llm_decision == 'read' for p in papers)}",
        f"- LLM 推荐略读：{sum(p.llm_decision == 'skim' for p in papers)}",
    ]
    if no_llm:
        lines.append("- 模式：未执行 LLM 评分，分组依据关键词规则分")
    sections = [
        ("强相关，建议精读", groups["read"]),
        ("中等相关，建议略读", groups["skim"]),
        ("AI SOTA / 方法进展", groups["ai"]),
        ("脑信号 / 神经科学相关", groups["brain"]),
        ("跳过但可留意", groups["skip"]),
    ]
    for heading, items in sections:
        lines.extend(["", f"## {heading}", ""])
        if not items:
            lines.append("_今日无论文。_")
        else:
            lines.extend(_paper_block(index, paper, no_llm) for index, paper in enumerate(items, 1))
    return "\n".join(lines).rstrip() + "\n"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
        path.chmod(0o644)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def write_daily_note(
    report_date: str,
    content: str,
    output_config: dict | None = None,
) -> list[Path]:
    output_config = output_config or load_yaml("output.yaml")
    parsed_date = date_type.fromisoformat(report_date)
    filename = parsed_date.strftime(output_config["daily_filename_format"])
    written: list[Path] = []
    targets: list[Path] = []
    if output_config.get("write_local_copy", True):
        targets.append(resolve_project_path(output_config.get("local_output_dir", "notes/daily")) / filename)
    obsidian = output_config.get("obsidian_output_dir")
    if obsidian:
        targets.append(resolve_project_path(obsidian) / filename)

    for target in dict.fromkeys(targets):
        try:
            _atomic_write(target, content)
            written.append(target)
        except OSError as exc:
            LOGGER.error("Could not write daily note to %s: %s", target, exc)
    if not written:
        raise OSError("Daily note could not be written to any configured output")
    return written
