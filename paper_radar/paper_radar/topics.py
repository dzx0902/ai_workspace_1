from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .markdown import _atomic_write
from .models import Paper
from .storage import PaperStorage
from .utils import load_yaml, resolve_project_path


def matches_topic(paper: Paper, topic: dict[str, Any]) -> bool:
    text = f"{paper.title} {paper.summary}".casefold()
    keyword_match = any(
        str(keyword).casefold() in text for keyword in topic.get("keywords", [])
    )
    categories = set(paper.llm_category)
    category_match = bool(categories & set(topic.get("required_categories", [])))
    return keyword_match or category_match


def _paper_lines(papers: list[Paper], limit: int = 20) -> str:
    if not papers:
        return "_暂无论文。_"
    return "\n".join(
        f"- [{paper.title}]({paper.url}) | {paper.source} | "
        f"{paper.llm_score if paper.llm_score is not None else paper.rule_score or 0:g}"
        for paper in papers[:limit]
    )


def _method_trends(papers: list[Paper]) -> str:
    terms = [
        "diffusion",
        "flow matching",
        "transformer",
        "contrastive learning",
        "foundation model",
        "multimodal",
        "reasoning",
        "agent",
        "RAG",
    ]
    counts = Counter()
    for paper in papers:
        text = f"{paper.title} {paper.summary}".casefold()
        for term in terms:
            if term.casefold() in text:
                counts[term] += 1
    return "\n".join(f"- {term}: {count} 篇" for term, count in counts.most_common()) or "- 暂无明显趋势"


def render_topic_note(topic: dict[str, Any], papers: list[Paper]) -> str:
    unread = [paper for paper in papers if not paper.feedback_read_later and not paper.paper_note_path]
    return f"""# {topic["name"]}

{topic.get("description", "")}

## 最近更新

{_paper_lines(papers, 10)}

## 代表论文

{_paper_lines([paper for paper in papers if (paper.llm_score or 0) >= 8], 10)}

## 方法趋势

{_method_trends(papers)}

## 数据集 / Benchmark

- 从单篇精读笔记和全文中持续补充。

## 和我研究方向的关系

- 关键词：{", ".join(topic.get("keywords", []))}
- 分类：{", ".join(topic.get("required_categories", []))}

## 可跟进问题

- 哪些方法具备跨被试、跨数据集或跨模态泛化？
- 哪些 AI 方法可以迁移到脑信号解码与生成式重建？

## 未读论文列表

{_paper_lines(unread, 30)}
"""


class TopicService:
    def __init__(self, storage: PaperStorage | None = None):
        self.storage = storage or PaperStorage()
        self.config = load_yaml("topics.yaml")

    def generate_topic(self, topic_name: str, days: int = 90) -> Path:
        topic = next(
            (
                value
                for value in self.config.get("topics", [])
                if value.get("enabled", True)
                and value.get("name", "").casefold() == topic_name.casefold()
            ),
            None,
        )
        if not topic:
            raise ValueError(f"Unknown or disabled topic: {topic_name}")
        end = date.today()
        papers = self.storage.get_papers_between(
            (end - timedelta(days=days)).isoformat(),
            end.isoformat(),
        )
        matched = [paper for paper in papers if matches_topic(paper, topic)]
        path = resolve_project_path(topic["output_path"])
        content = render_topic_note(topic, matched)
        _atomic_write(path, content)
        obsidian_dir = self.config.get("obsidian_topic_dir")
        if obsidian_dir:
            try:
                _atomic_write(
                    resolve_project_path(obsidian_dir) / path.name,
                    content,
                )
            except OSError:
                pass
        return path

    def generate_all_topics(self, days: int = 90) -> list[Path]:
        return [
            self.generate_topic(topic["name"], days)
            for topic in self.config.get("topics", [])
            if topic.get("enabled", True)
        ]

    def generate_review(self, end_date: date, period: str) -> Path:
        if period == "weekly":
            start = end_date - timedelta(days=6)
            title = f"Paper Radar Weekly Review - {start} to {end_date}"
            output_dir = self.config["weekly_output_dir"]
            filename = f"{end_date}-weekly-review.md"
        elif period == "monthly":
            start = end_date.replace(day=1)
            title = f"Paper Radar Monthly Review - {end_date:%Y-%m}"
            output_dir = self.config["monthly_output_dir"]
            filename = f"{end_date:%Y-%m}-monthly-review.md"
        else:
            raise ValueError(f"Unsupported review period: {period}")
        papers = self.storage.get_papers_between(start.isoformat(), end_date.isoformat())
        strong = [paper for paper in papers if (paper.llm_score or 0) >= 8]
        ai = [
            paper
            for paper in papers
            if set(paper.llm_category) & {"ai_core", "ai_sota"}
        ]
        brain = [
            paper
            for paper in papers
            if set(paper.llm_category)
            & {"brain_signal", "brain_decoding", "neuroscience"}
        ]
        if period == "weekly":
            content = f"""# {title}

## 本周强相关论文
{_paper_lines(strong)}

## 本周 AI SOTA 进展
{_paper_lines(ai)}

## 本周脑信号 / 神经科学进展
{_paper_lines(brain)}

## 值得精读的 3-5 篇
{_paper_lines(strong, 5)}

## 可能用于自己课题的想法
{_method_trends(strong)}
"""
        else:
            content = f"""# {title}

## 方向趋势总结
{_method_trends(papers)}

## 高价值论文列表
{_paper_lines(strong, 30)}

## 方法路线图
{_method_trends(ai)}

## 可以写进 related work 的内容
{_paper_lines([paper for paper in papers if paper.feedback_related_work], 30)}

## 可能的实验灵感
{_method_trends(brain)}
"""
        path = resolve_project_path(output_dir) / filename
        _atomic_write(path, content)
        obsidian_dir = self.config.get("obsidian_review_dir")
        if obsidian_dir:
            try:
                _atomic_write(resolve_project_path(obsidian_dir) / filename, content)
            except OSError:
                pass
        return path
