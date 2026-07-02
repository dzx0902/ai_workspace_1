from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from sentence_transformers import SentenceTransformer

from scripts.config import get_embed_config


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    cfg = get_embed_config()
    if cfg.provider != "local":
        raise ValueError("Current setup only supports local embedding.")
    return SentenceTransformer(cfg.model, device=cfg.device)


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    model = get_embedder()
    vectors = model.encode(
        list(texts),
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
