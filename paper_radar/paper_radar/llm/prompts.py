from __future__ import annotations

import json

from ..models import Paper

SYSTEM_PROMPT = """你是严谨的科研论文初筛助手。只依据给定标题和摘要判断，不要补充不存在的信息。
你的输出必须是一个 JSON 对象，不要使用 Markdown，不要输出解释性前后缀。"""


def build_scoring_prompt(paper: Paper) -> str:
    matched = [
        f"{item.get('topic')}: {item.get('keyword')} ({item.get('field')})"
        for item in paper.matched_keywords
    ]
    return f"""请评估以下论文与我的研究兴趣的相关性。

研究兴趣：
- 脑信号：EEG、fMRI、MEG、ECoG、EMG、EOG、BCI、生理信号
- 脑解码：神经解码、视觉/听觉解码、图像/视频/刺激重建
- 神经科学：神经影像、认知神经科学、计算神经科学、神经表征
- AI 方法：多模态学习、CLIP、diffusion、flow matching、VLM、foundation model
- AI 前沿：LLM、agent、reasoning、benchmark、post-training、test-time scaling、RAG、world model、tool use

论文信息：
title: {paper.title}
abstract: {paper.summary}
source: {paper.source}
category: {paper.source_category}
matched_keywords: {json.dumps(matched, ensure_ascii=False)}

严格返回以下 JSON：
{{
  "relevance_score": 0到10之间的数字,
  "category": ["brain_signal", "brain_decoding", "neuroscience", "ai_core", "ai_sota", "irrelevant"] 中的一个或多个值,
  "decision": "read" 或 "skim" 或 "skip",
  "reason": "不超过80字的中文说明",
  "keywords": ["最相关的关键词"],
  "note_priority": "high" 或 "medium" 或 "low"
}}
"""
