from __future__ import annotations

import json
import os
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from ..models import Paper
from ..utils import LOG_DIR
from .router import LLMConfig, _extract_json, get_llm_config

FULL_PAPER_SYSTEM_PROMPT = """你是严谨的科研论文精读助手。只能依据给出的论文全文，
不确定或正文未报告的内容必须明确写“未报告”，不得补造实验、数据或结论。
输出必须是单个 JSON 对象，不要使用 Markdown 代码块或解释性前后缀。"""

_REQUIRED_TEXT_FIELDS = (
    "sentence_summary",
    "research_question",
    "method_overview",
    "datasets_experiments",
    "key_results",
    "research_relevance",
    "limitations_questions",
)
_REQUIRED_LIST_FIELDS = ("core_contributions", "transferable_ideas", "tags")


def paper_kind(paper: Paper) -> str:
    brain_categories = {"brain_signal", "brain_decoding", "neuroscience"}
    if set(paper.llm_category) & brain_categories:
        return "brain_signal"
    text = f"{paper.title} {paper.summary}".casefold()
    brain_terms = (
        "eeg",
        "fmri",
        "meg",
        "ecog",
        "brain-computer",
        "neural decoding",
        "neuroimaging",
    )
    return "brain_signal" if any(term in text for term in brain_terms) else "ai_method"


def build_fullpaper_prompt(paper: Paper, fulltext: str) -> str:
    if paper_kind(paper) == "brain_signal":
        focus = """这是脑信号/神经科学论文。重点提取：
- 信号类型（EEG/fMRI/MEG/ECoG/EMG/EOG）
- 任务（分类、重建、解码、生成、对齐）
- 数据集、模型结构
- 跨被试与跨数据集泛化
- 与 EEG/fMRI decoding 的关系"""
    else:
        focus = """这是 AI 方法/SOTA 论文。重点提取：
- 模型架构变化与训练目标
- 数据规模和 benchmark
- 相比既有方法的关键差异
- 能否迁移到脑信号建模、多模态对齐和生成式解码"""
    return f"""请精读以下论文并进行结构化总结。

{focus}

论文元数据：
- title: {paper.title}
- authors: {", ".join(paper.authors)}
- source: {paper.source}
- categories: {json.dumps(paper.llm_category, ensure_ascii=False)}
- score: {paper.llm_score}

严格返回以下 JSON：
{{
  "sentence_summary": "一句话总结",
  "research_question": "研究问题",
  "core_contributions": ["核心贡献"],
  "method_overview": "方法概述",
  "datasets_experiments": "数据集与实验设置",
  "key_results": "关键结果，尽量包含正文明确报告的数字",
  "research_relevance": "与用户研究方向的关系",
  "transferable_ideas": ["可借鉴之处"],
  "limitations_questions": "局限与疑问",
  "tags": ["标签"]
}}

论文全文：
--- FULLTEXT START ---
{fulltext}
--- FULLTEXT END ---
"""


def validate_fullpaper_result(value: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in _REQUIRED_TEXT_FIELDS:
        text = str(value.get(field, "")).strip()
        if not text:
            raise ValueError(f"Missing full-paper summary field: {field}")
        result[field] = text
    for field in _REQUIRED_LIST_FIELDS:
        items = value.get(field)
        if isinstance(items, str):
            items = [items]
        if not isinstance(items, list):
            raise ValueError(f"Full-paper summary field must be a list: {field}")
        result[field] = [str(item).strip() for item in items if str(item).strip()]
    return result


class FullPaperSummarizer:
    def __init__(self, config: LLMConfig | None = None):
        config = config or get_llm_config()
        strong_model = os.getenv("PAPER_RADAR_STRONG_MODEL", "").strip()
        self.config = replace(config, model=strong_model) if strong_model else config
        if not self.config.api_key:
            raise RuntimeError(f"API key is empty for provider {self.config.provider}")
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            max_retries=0,
        )
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def _save_raw(self, paper: Paper, content: str) -> Path:
        output_dir = LOG_DIR / "llm_raw"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(
            value if value.isalnum() or value in "._-" else "_"
            for value in paper.id
        )
        path = output_dir / f"{safe_id}-fullpaper.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def summarize(self, paper: Paper, fulltext: str) -> dict[str, Any]:
        retryable = (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            InternalServerError,
        )
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": FULL_PAPER_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": build_fullpaper_prompt(paper, fulltext),
                        },
                    ],
                    temperature=0.1,
                    max_tokens=3500,
                )
                content = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
                self.last_usage = {
                    "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "completion_tokens": int(
                        getattr(usage, "completion_tokens", 0) or 0
                    ),
                }
                try:
                    return validate_fullpaper_result(_extract_json(content))
                except (ValueError, json.JSONDecodeError) as exc:
                    self._save_raw(paper, content)
                    last_error = exc
            except retryable as exc:
                last_error = exc
            if attempt + 1 < self.config.max_retries:
                time.sleep(2**attempt)
        raise RuntimeError(f"Full-paper summarization failed: {last_error}")
