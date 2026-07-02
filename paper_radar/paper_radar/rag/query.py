from __future__ import annotations

from typing import Any, Callable

from ..llm.router import get_llm_config
from ..utils import load_yaml
from .client import Embedder, chroma_collection


class PaperRAGQuery:
    def __init__(
        self,
        config: dict[str, Any] | None = None,
        collection=None,
        embed: Callable[[list[str]], list[list[float]]] | None = None,
    ):
        self.config = config or load_yaml("rag.yaml")
        self.collection = collection or chroma_collection(self.config)
        self.embed = embed or Embedder(self.config).embed

    def retrieve(self, question: str, n_results: int | None = None) -> list[dict]:
        result = self.collection.query(
            query_embeddings=self.embed([question]),
            n_results=n_results or int(self.config.get("query_results", 6)),
            include=["documents", "metadatas", "distances"],
        )
        return [
            {"document": doc, "metadata": meta, "distance": distance}
            for doc, meta, distance in zip(
                result.get("documents", [[]])[0],
                result.get("metadatas", [[]])[0],
                result.get("distances", [[]])[0],
            )
        ]

    def answer(self, question: str, use_llm: bool = False) -> str:
        hits = self.retrieve(question)
        if not hits:
            return "本地论文知识库中没有找到相关内容。"
        citations = []
        for index, hit in enumerate(hits, 1):
            meta = hit["metadata"]
            citations.append(
                f"[{index}] {meta.get('title', '-')} | {meta.get('url', '-')} | "
                f"{meta.get('note_path', '-')} | chunk {meta.get('chunk_index', '-')}"
            )
        if not use_llm:
            previews = [
                f"### [{index}] {hit['metadata'].get('title', '-')}\n"
                f"{hit['document'][:500]}"
                for index, hit in enumerate(hits, 1)
            ]
            return "\n\n".join(previews) + "\n\n## 引用来源\n" + "\n".join(citations)

        from openai import OpenAI

        config = get_llm_config()
        if not config.api_key:
            raise RuntimeError(f"API key is empty for provider {config.provider}")
        context = "\n\n".join(
            f"[{index}] {hit['document']}" for index, hit in enumerate(hits, 1)
        )
        response = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        ).chat.completions.create(
            model=config.model,
            messages=[
                {
                    "role": "system",
                    "content": "仅依据检索内容用中文回答，并用 [数字] 标注引用。资料不足要明确说明。",
                },
                {
                    "role": "user",
                    "content": f"问题：{question}\n\n检索内容：\n{context}",
                },
            ],
            temperature=0.1,
            max_tokens=1800,
        )
        answer = response.choices[0].message.content or ""
        return answer + "\n\n## 引用来源\n" + "\n".join(citations)
