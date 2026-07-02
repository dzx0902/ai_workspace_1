from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import requests
from openai import OpenAI

from ..utils import load_environment


@lru_cache(maxsize=2)
def _local_model(model: str, device: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model, device=device, local_files_only=True)


class Embedder:
    def __init__(self, config: dict[str, Any]):
        load_environment()
        self.provider = os.getenv(
            "PAPER_RADAR_EMBED_PROVIDER",
            str(config.get("embedding_provider", "ollama")),
        ).lower()
        self.model = os.getenv(
            "PAPER_RADAR_EMBED_MODEL",
            str(config.get("embedding_model", "nomic-embed-text")),
        )
        self.ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL",
            str(config.get("ollama_base_url", "http://127.0.0.1:11434")),
        ).rstrip("/")
        self.device = os.getenv(
            "PAPER_RADAR_EMBED_DEVICE",
            str(config.get("embedding_device", "cpu")),
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "local":
            return _local_model(self.model, self.device).encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()
        if self.provider == "ollama":
            session = requests.Session()
            session.trust_env = False
            response = session.post(
                f"{self.ollama_base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            embeddings = payload.get("embeddings")
            if not embeddings:
                raise RuntimeError("Ollama embedding response did not contain embeddings")
            return embeddings
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings")
            client = OpenAI(
                api_key=api_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            )
            response = client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        raise ValueError(f"Unsupported embedding provider: {self.provider}")


def chroma_collection(config: dict[str, Any]):
    import chromadb

    host = os.getenv("CHROMA_HOST", str(config.get("chroma_host", "localhost")))
    port = int(os.getenv("CHROMA_PORT", str(config.get("chroma_port", 8000))))
    name = os.getenv(
        "PAPER_RADAR_CHROMA_COLLECTION",
        str(config.get("collection", "paper_radar")),
    )
    client = chromadb.HttpClient(host=host, port=port)
    return client.get_or_create_collection(name=name)
