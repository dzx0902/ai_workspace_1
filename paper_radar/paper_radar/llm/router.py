from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, replace
from typing import Any

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from ..models import Paper
from ..utils import load_environment
from .prompts import SYSTEM_PROMPT, build_scoring_prompt

_CATEGORIES = {
    "brain_signal",
    "brain_decoding",
    "neuroscience",
    "ai_core",
    "ai_sota",
    "irrelevant",
}
_DECISIONS = {"read", "skim", "skip"}
_PRIORITIES = {"high", "medium", "low"}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    timeout: float
    max_retries: int


def get_llm_config() -> LLMConfig:
    load_environment()
    provider = os.getenv(
        "PAPER_RADAR_LLM_PROVIDER",
        os.getenv("GEN_PROVIDER", os.getenv("LLM_PROVIDER", "deepseek")),
    ).lower()
    prefix = {
        "deepseek": "DEEPSEEK",
        "dashscope": "DASHSCOPE",
        "siliconflow": "SILICONFLOW",
        "openai": "OPENAI",
    }.get(provider)
    if not prefix:
        raise ValueError(f"Unsupported LLM provider: {provider}")
    defaults = {
        "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
        "dashscope": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
        "siliconflow": ("https://api.siliconflow.cn/v1", "Qwen/Qwen2.5-7B-Instruct"),
        "openai": ("https://api.openai.com/v1", "gpt-4.1-mini"),
    }
    default_url, default_model = defaults[provider]
    return LLMConfig(
        provider=provider,
        api_key=os.getenv(f"{prefix}_API_KEY", ""),
        base_url=os.getenv(f"{prefix}_BASE_URL", default_url),
        model=os.getenv(f"{prefix}_MODEL", default_model),
        timeout=float(os.getenv("PAPER_RADAR_LLM_TIMEOUT", "60")),
        max_retries=int(os.getenv("PAPER_RADAR_LLM_MAX_RETRIES", "3")),
    )


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence:
        cleaned = fence.group(1)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM response did not contain a JSON object")
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM response JSON must be an object")
    return value


def validate_result(value: dict[str, Any]) -> dict[str, Any]:
    try:
        score = float(value["relevance_score"])
        categories = value["category"]
        decision = str(value["decision"])
        reason = str(value["reason"]).strip()
        keywords = value["keywords"]
        priority = str(value["note_priority"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Missing or invalid LLM result field: {exc}") from exc
    if not 0 <= score <= 10:
        raise ValueError("relevance_score must be between 0 and 10")
    if isinstance(categories, str):
        categories = [categories]
    if not isinstance(categories, list) or not categories:
        raise ValueError("category must be a non-empty list")
    categories = [str(item) for item in categories]
    if any(item not in _CATEGORIES for item in categories):
        raise ValueError(f"Invalid category: {categories}")
    if decision not in _DECISIONS:
        raise ValueError(f"Invalid decision: {decision}")
    if priority not in _PRIORITIES:
        raise ValueError(f"Invalid note_priority: {priority}")
    if not isinstance(keywords, list):
        raise ValueError("keywords must be a list")
    return {
        "relevance_score": score,
        "category": categories,
        "decision": decision,
        "reason": reason[:500],
        "keywords": [str(item) for item in keywords],
        "note_priority": priority,
    }


class PaperLLMScorer:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or get_llm_config()
        cheap_model = os.getenv("PAPER_RADAR_CHEAP_MODEL", "").strip()
        if cheap_model:
            self.config = replace(self.config, model=cheap_model)
        if not self.config.api_key:
            raise RuntimeError(f"API key is empty for provider {self.config.provider}")
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            max_retries=0,
        )
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def score(self, paper: Paper) -> dict[str, Any]:
        retryable = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": build_scoring_prompt(paper)},
                    ],
                    temperature=0.1,
                    max_tokens=600,
                )
                content = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
                self.last_usage = {
                    "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "completion_tokens": int(
                        getattr(usage, "completion_tokens", 0) or 0
                    ),
                }
                return validate_result(_extract_json(content))
            except retryable:
                if attempt + 1 >= self.config.max_retries:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("LLM scoring exhausted without a response")
