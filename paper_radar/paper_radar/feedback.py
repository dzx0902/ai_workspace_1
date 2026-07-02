from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .models import Paper
from .storage import PaperStorage

PAPER_ID_RE = re.compile(r"<!--\s*paper_id:\s*(.+?)\s*-->")
CHECK_RE = re.compile(r"^-\s*\[([ xX])\]\s*(.+?)\s*$", re.MULTILINE)
LABELS = {
    "relevant": "relevant",
    "not relevant": "not_relevant",
    "read later": "read_later",
    "add to related work": "related_work",
    "summarize full paper": "summarize",
}


def parse_feedback(content: str) -> dict[str, dict[str, bool]]:
    matches = list(PAPER_ID_RE.finditer(content))
    result: dict[str, dict[str, bool]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[match.end() : end]
        feedback = {value: False for value in LABELS.values()}
        for checked, label in CHECK_RE.findall(block):
            key = LABELS.get(label.strip().casefold())
            if key:
                feedback[key] = checked.casefold() == "x"
        result[match.group(1).strip()] = feedback
    return result


def collect_feedback(paths: list[Path], storage: PaperStorage) -> dict[str, int]:
    counts = {"files": 0, "papers": 0, "missing": 0}
    for path in paths:
        if not path.exists() or path.suffix.lower() != ".md":
            continue
        counts["files"] += 1
        for paper_id, feedback in parse_feedback(
            path.read_text(encoding="utf-8", errors="ignore")
        ).items():
            if storage.get_paper(paper_id) is None:
                counts["missing"] += 1
                continue
            storage.update_feedback(paper_id, feedback)
            counts["papers"] += 1
    return counts


def feedback_adjustment(paper: Paper, feedback_papers: list[Paper]) -> int:
    positive_keywords: Counter[str] = Counter()
    negative_keywords: Counter[str] = Counter()
    source_score: Counter[str] = Counter()
    for item in feedback_papers:
        positive = bool(
            item.feedback_relevant
            or item.feedback_related_work
            or item.feedback_summarize
        )
        negative = bool(item.feedback_not_relevant)
        if positive:
            source_score[item.source] += 1
        if negative:
            source_score[item.source] -= 1
        for match in item.matched_keywords:
            keyword = str(match.get("keyword", "")).casefold()
            if keyword and positive:
                positive_keywords[keyword] += 1
            if keyword and negative:
                negative_keywords[keyword] += 1
    adjustment = max(-2, min(2, source_score[paper.source]))
    text = f"{paper.title} {paper.summary}".casefold()
    for keyword, count in positive_keywords.items():
        if keyword in text:
            adjustment += min(2, count)
    for keyword, count in negative_keywords.items():
        if keyword in text:
            adjustment -= min(2, count)
    return max(-5, min(5, adjustment))
