from pathlib import Path

from paper_radar.feedback import collect_feedback, feedback_adjustment, parse_feedback
from paper_radar.models import Paper
from paper_radar.storage import PaperStorage


def make_paper(paper_id: str = "p1") -> Paper:
    return Paper(
        id=paper_id,
        title="EEG decoding",
        source="arxiv",
        url=f"https://example.org/{paper_id}",
        fetched_at="2026-06-11T08:00:00+08:00",
        matched_keywords=[{"keyword": "EEG"}],
    )


def test_parse_and_collect_feedback(tmp_path):
    content = """### Paper
<!-- paper_id: p1 -->
- [x] relevant
- [ ] not relevant
- [x] read later
- [ ] add to related work
- [x] summarize full paper
"""
    parsed = parse_feedback(content)
    assert parsed["p1"]["relevant"] is True
    storage = PaperStorage(tmp_path / "papers.db")
    storage.upsert_paper(make_paper())
    note = tmp_path / "daily.md"
    note.write_text(content, encoding="utf-8")
    counts = collect_feedback([note], storage)
    assert counts["papers"] == 1
    saved = storage.get_paper("p1")
    assert saved.feedback_relevant == 1
    assert saved.feedback_summarize == 1


def test_feedback_adjustment_rewards_positive_keywords():
    history = make_paper("history")
    history.feedback_relevant = 1
    candidate = make_paper("candidate")
    assert feedback_adjustment(candidate, [history]) > 0
