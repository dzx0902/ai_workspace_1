from pathlib import Path

from paper_radar.models import Paper
from paper_radar.rag.chunker import chunk_text
from paper_radar.rag.ingest import PaperRAGIngestor
from paper_radar.storage import PaperStorage


class FakeCollection:
    def __init__(self):
        self.payload = None

    def upsert(self, **kwargs):
        self.payload = kwargs

    def delete(self, **kwargs):
        pass


def test_chunk_text_preserves_content():
    chunks = chunk_text("first paragraph\n\nsecond paragraph", 20, 5)
    assert chunks
    assert "first" in chunks[0]


def test_ingest_path_has_required_metadata(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    paper = Paper(
        id="p1",
        title="EEG paper",
        source="arxiv",
        source_category="q-bio.NC",
        url="https://example.org/p1",
        pdf_url="https://example.org/p1.pdf",
        published="2026-06-11",
        fetched_at="2026-06-11T08:00:00+08:00",
        llm_category=["brain_signal"],
    )
    path = tmp_path / "paper.md"
    path.write_text("# EEG paper\n\ncontent", encoding="utf-8")
    collection = FakeCollection()
    ingestor = PaperRAGIngestor(
        storage=storage,
        config={
            "manifest_path": str(tmp_path / "manifest.json"),
            "chunk_size": 100,
            "chunk_overlap": 10,
        },
        collection=collection,
        embed=lambda texts: [[0.1, 0.2] for _ in texts],
    )
    assert ingestor.ingest_path(path, "paper", paper) == 1
    metadata = collection.payload["metadatas"][0]
    assert metadata["paper_id"] == "p1"
    assert metadata["note_type"] == "paper"
    assert metadata["note_path"] == str(path.resolve())
