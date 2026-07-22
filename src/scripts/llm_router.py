from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from openai import OpenAI
import requests

from scripts.config import (
    GEN_PROVIDER,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    DASHSCOPE_MODEL,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_MODEL,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    AI_PLATFORM_LLM_URL,
    get_embed_config,
)


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer

    cfg = get_embed_config()
    if cfg.provider != 'local':
        raise RuntimeError('Only local embedding is enabled in this workspace.')

    model_path = Path(cfg.model).expanduser().resolve()
    if not model_path.exists():
        raise FileNotFoundError(
            f'Local embedding model not found: {model_path}. '
            'Set EMBED_MODEL to an existing local sentence-transformers model, '
            'for example /mnt/f/AIModels/bge-small-zh-v1.5. No HuggingFace download was attempted.'
        )

    return SentenceTransformer(str(model_path), device=cfg.device, local_files_only=True)


def local_embed(text: str) -> list[float]:
    cfg = get_embed_config()
    if cfg.provider != 'local':
        if AI_PLATFORM_LLM_URL:
            embedding_url = AI_PLATFORM_LLM_URL.rsplit('/', 1)[0] + '/embeddings'
            response = requests.post(embedding_url, json={'input': text, 'model': cfg.model}, timeout=120)
            response.raise_for_status()
            return response.json()['data'][0]['embedding']
        api_key = DEEPSEEK_API_KEY if cfg.provider == 'deepseek' else os.getenv('OPENAI_API_KEY', '')
        base_url = DEEPSEEK_BASE_URL if cfg.provider == 'deepseek' else os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        if not api_key:
            raise RuntimeError(f'Embedding API key is empty for provider {cfg.provider}.')
        response = OpenAI(api_key=api_key, base_url=base_url).embeddings.create(model=cfg.model, input=text)
        return response.data[0].embedding
    model = get_embedder()
    emb = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
    return emb.tolist()


def call_openai_compatible(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    max_tokens: int = LLM_MAX_TOKENS,
    temperature: float = LLM_TEMPERATURE,
) -> str:
    if not api_key:
        raise RuntimeError(f'API key is empty. Please check .env for provider base_url={base_url}')

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                'role': 'system',
                'content': (
                    '你是一个严谨的中文学习、科研和编程助手。'
                    '回答要结构清晰，避免编造；如果资料不足，要明确说明。'
                    'Markdown 标题只使用 #### 和 #####。'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ''


def deepseek_generate(prompt: str) -> str:
    return call_openai_compatible(prompt, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL)


def dashscope_generate(prompt: str) -> str:
    return call_openai_compatible(prompt, DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, DASHSCOPE_MODEL)


def siliconflow_generate(prompt: str) -> str:
    return call_openai_compatible(prompt, SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL, SILICONFLOW_MODEL)


def generate(prompt: str, mode: str = 'auto') -> str:
    if AI_PLATFORM_LLM_URL and mode in ('auto', 'api'):
        response = requests.post(
            AI_PLATFORM_LLM_URL,
            json={
                'messages': [
                    {'role': 'system', 'content': '你是一个严谨的中文学习、科研和编程助手。回答要结构清晰，避免编造。'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': LLM_TEMPERATURE,
                'max_tokens': LLM_MAX_TOKENS,
            },
            timeout=120,
        )
        response.raise_for_status()
        return str(response.json().get('content', ''))
    provider = GEN_PROVIDER if mode in ('auto', 'api') else mode
    provider = provider.lower().strip()
    if provider == 'deepseek':
        return deepseek_generate(prompt)
    if provider == 'dashscope':
        return dashscope_generate(prompt)
    if provider == 'siliconflow':
        return siliconflow_generate(prompt)
    raise ValueError(f'Unknown generation provider: {provider}')
