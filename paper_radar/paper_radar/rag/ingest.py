from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Callable

from ..models import Paper
from ..storage import PaperStorage
from ..utils import load_yaml, now_iso, resolve_project_path
from .chunker import chunk_text
from .client import Embedder, chroma_collection

LOGGER = logging.getLogger("paper_radar.rag.ingest")

def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PaperRAGIngestor:
    def __init__(
        self,
        storage: PaperStorage | None = None,
        config: dict[str, Any] | None = None,
        collection=None,
        embed: Callable[[list[str]], list[list[float]]] | None = None,
    ):
        self.storage = storage or PaperStorage()
        self.config = config or load_yaml("rag.yaml")
        self.collection = collection or chroma_collection(self.config)
        self.embed = embed or Embedder(self.config).embed
        self.manifest_path = resolve_project_path(self.config["manifest_path"])

    def _manifest(self) -> dict[str, Any]:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {}

    def _save_manifest(self, value: dict[str, Any]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def ingest_path(
        self,
        path: Path,
        note_type: str,
        paper: Paper | None = None,
        force: bool = False,
    ) -> int:
        path = path.expanduser().resolve()
        manifest = self._manifest()
        key = f"{path}|{note_type}"
        digest = _hash(path)
        if not force and manifest.get(key, {}).get("hash") == digest:
            return 0
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_text(
            text,
            int(self.config.get("chunk_size", 1200)),
            int(self.config.get("chunk_overlap", 200)),
        )
        if not chunks:
            return 0
        ids = [
            hashlib.sha256(f"{key}:{index}:{chunk}".encode()).hexdigest()
            for index, chunk in enumerate(chunks)
        ]
        tags = ",".join(paper.llm_category) if paper else ""
        metadata = {
            "paper_id": paper.id if paper else "",
            "title": paper.title if paper else path.stem,
            "source": paper.source if paper else "paper_radar",
            "source_category": paper.source_category if paper else "",
            "published": paper.published if paper else "",
            "tags": tags,
            "note_type": note_type,
            "url": paper.url if paper else "",
            "pdf_url": paper.pdf_url if paper else "",
            "note_path": str(path),
            "ingested_at": now_iso(),
        }
        metas = [{**metadata, "chunk_index": index} for index in range(len(chunks))]
        self.collection.delete(where={"note_path": str(path)})
        self.collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metas,
            embeddings=self.embed(chunks),
        )
        manifest[key] = {"hash": digest, "chunks": len(chunks)}
        self._save_manifest(manifest)
        return len(chunks)

    def ingest_all(self, force: bool = False) -> dict[str, int]:
        counts = {"files": 0, "chunks": 0, "skipped": 0}
        papers = self.storage.get_papers_between("0001-01-01", "9999-12-31")
        paths: list[tuple[Path, str, Paper | None]] = []
        for paper in papers:
            if paper.paper_note_path:
                paths.append((Path(paper.paper_note_path), "paper", paper))
            if paper.extracted_text_path:
                paths.append((Path(paper.extracted_text_path), "fulltext", paper))
        for path in resolve_project_path("notes/daily").glob("*.md"):
            paths.append((path, "daily", None))
        for path in resolve_project_path("notes/topics").glob("*.md"):
            paths.append((path, "topic", None))
        for path, note_type, paper in paths:
            if not path.exists():
                continue
            try:
                chunks = self.ingest_path(path, note_type, paper, force)
            except OSError as exc:
                LOGGER.error("Could not ingest %s: %s", path, exc)
                continue
            counts["files"] += 1
            counts["chunks"] += chunks
            counts["skipped"] += int(chunks == 0)
        return counts
