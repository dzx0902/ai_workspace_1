from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import Paper
from .utils import load_yaml


@dataclass(frozen=True)
class RuleResult:
    score: int
    matches: list[dict[str, str]]


def decision_for_score(score: float, scoring_config: dict[str, Any] | None = None) -> str:
    scoring_config = scoring_config or load_yaml("scoring.yaml")
    for decision in ("read", "skim", "skip"):
        value_range = scoring_config.get("decision_ranges", {}).get(decision, {})
        if float(value_range.get("min", 0)) <= score <= float(value_range.get("max", 10)):
            return decision
    raise ValueError(f"No configured decision range contains score {score}")


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    parts = re.split(r"\s+", keyword.strip())
    normalized = r"\s+".join(re.escape(part) for part in parts)
    if re.fullmatch(r"[A-Za-z0-9-]+", keyword.strip()):
        pattern = rf"(?<![A-Za-z0-9]){normalized}(?![A-Za-z0-9])"
    else:
        pattern = normalized
    return re.compile(pattern, re.IGNORECASE)


def score_paper(
    paper: Paper,
    keywords_config: dict[str, Any] | None = None,
    scoring_config: dict[str, Any] | None = None,
) -> RuleResult:
    keywords_config = keywords_config or load_yaml("keywords.yaml")
    scoring_config = scoring_config or load_yaml("scoring.yaml")
    weights = scoring_config["weights"]
    fields = {"title": paper.title or "", "abstract": paper.summary or ""}
    score = 0
    matches: list[dict[str, str]] = []

    for topic, levels in keywords_config.get("topics", {}).items():
        for level in ("high", "medium"):
            for keyword in levels.get(level, []):
                pattern = _keyword_pattern(str(keyword))
                for field, text in fields.items():
                    if pattern.search(text):
                        score += int(weights[field][level])
                        matches.append(
                            {
                                "topic": topic,
                                "level": level,
                                "field": field,
                                "keyword": str(keyword),
                            }
                        )
    return RuleResult(score=score, matches=matches)
