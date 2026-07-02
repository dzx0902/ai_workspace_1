from datetime import date

from paper_radar.models import Paper
from paper_radar.storage import PaperStorage
from paper_radar.topics import TopicService, matches_topic


def make_paper() -> Paper:
    return Paper(
        id="p1",
        title="Diffusion models for EEG image reconstruction",
        source="arxiv",
        url="https://example.org/p1",
        fetched_at="2026-06-11T08:00:00+08:00",
        llm_score=9,
        llm_category=["brain_decoding", "ai_core"],
    )


def test_topic_matching_by_keyword_and_category():
    assert matches_topic(
        make_paper(),
        {"keywords": ["EEG"], "required_categories": ["brain_signal"]},
    )


def test_weekly_review_writes_file(tmp_path, monkeypatch):
    storage = PaperStorage(tmp_path / "papers.db")
    storage.upsert_paper(make_paper())
    service = TopicService(storage)
    service.config["weekly_output_dir"] = str(tmp_path / "weekly")
    service.config["obsidian_review_dir"] = None
    path = service.generate_review(date(2026, 6, 11), "weekly")
    assert path.exists()
    assert "本周强相关论文" in path.read_text(encoding="utf-8")


def test_topic_note_writes_obsidian_copy(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    storage.upsert_paper(make_paper())
    service = TopicService(storage)
    service.config["topics"] = [
        {
            "name": "EEG",
            "keywords": ["EEG"],
            "required_categories": [],
            "output_path": str(tmp_path / "local" / "eeg.md"),
            "enabled": True,
        }
    ]
    service.config["obsidian_topic_dir"] = str(tmp_path / "obsidian")
    path = service.generate_topic("EEG")
    assert path.exists()
    assert (tmp_path / "obsidian" / "eeg.md").exists()
