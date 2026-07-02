import sqlite3

from paper_radar.models import Paper
from paper_radar.storage import PaperStorage


def make_paper(title: str = "First title") -> Paper:
    return Paper(
        id="2401.00001",
        title=title,
        authors=["Researcher"],
        summary="EEG decoding",
        source="arxiv",
        source_category="q-bio.NC",
        url="https://arxiv.org/abs/2401.00001",
        pdf_url="https://arxiv.org/pdf/2401.00001.pdf",
        published="2024-01-01",
        fetched_at="2026-06-08T10:00:00+08:00",
    )


def test_upsert_deduplicates_and_preserves_scores(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    assert storage.upsert_paper(make_paper()) is True
    storage.update_rule_result("2401.00001", 9, [{"topic": "brain_signals"}], "llm_pending")

    assert storage.upsert_paper(make_paper("Updated title")) is False
    papers = storage.get_llm_pending()
    assert len(papers) == 1
    assert papers[0].title == "Updated title"
    assert papers[0].rule_score == 9


def test_date_query_uses_fetched_date(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    storage.upsert_paper(make_paper())
    assert len(storage.get_candidates_for_date("2026-06-08")) == 1
    assert storage.get_candidates_for_date("2026-06-09") == []


def test_llm_pending_can_select_top_papers_for_date(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    papers = [
        make_paper("Older"),
        make_paper("Today lower"),
        make_paper("Today higher"),
    ]
    for index, paper in enumerate(papers):
        paper.id = f"paper-{index}"
        paper.url = f"https://example.com/paper-{index}"
    papers[1].fetched_at = "2026-06-11T08:00:00+08:00"
    papers[2].fetched_at = "2026-06-11T09:00:00+08:00"
    for paper, score in zip(papers, (99, 10, 20)):
        storage.upsert_paper(paper)
        storage.update_rule_result(paper.id, score, [], "llm_pending")

    selected = storage.get_llm_pending(limit=2, date="2026-06-11")

    assert [paper.id for paper in selected] == ["paper-2", "paper-1"]


def test_init_db_migrates_existing_database(tmp_path):
    db_path = tmp_path / "papers.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE papers (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT NOT NULL DEFAULT '[]',
                summary TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL,
                source_category TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL UNIQUE,
                pdf_url TEXT NOT NULL DEFAULT '',
                published TEXT NOT NULL DEFAULT '',
                fetched_at TEXT NOT NULL,
                rule_score INTEGER,
                matched_keywords TEXT NOT NULL DEFAULT '[]',
                llm_score REAL,
                llm_category TEXT NOT NULL DEFAULT '[]',
                llm_decision TEXT NOT NULL DEFAULT '',
                llm_reason TEXT NOT NULL DEFAULT '',
                note_priority TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'fetched',
                llm_error TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            INSERT INTO papers (
                id, title, source, url, fetched_at
            ) VALUES ('2401.00001', 'Old paper', 'arxiv',
                      'https://arxiv.org/abs/2401.00001', '2026-06-08')
            """
        )

    storage = PaperStorage(db_path)
    paper = storage.get_paper("2401.00001")
    assert paper.external_id == "2401.00001"
    assert paper.pdf_download_status == ""


def test_pdf_candidates_require_high_priority_and_score(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    selected = make_paper("Selected")
    selected.llm_score = 9
    selected.llm_decision = "read"
    selected.note_priority = "high"
    selected.status = "scored"
    storage.upsert_paper(selected)
    storage.update_llm_result(
        selected.id,
        {
            "relevance_score": 9,
            "category": ["brain_signal"],
            "decision": "read",
            "reason": "relevant",
            "note_priority": "high",
        },
    )

    candidates = storage.get_pdf_candidates(8, ["arxiv"])
    assert [paper.id for paper in candidates] == ["2401.00001"]


def test_llm_usage_summary(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    storage.record_llm_usage("p1", "screening", "test", "model", 100, 20, 0.01)
    usage = storage.llm_usage_summary()
    assert usage["calls"] == 1
    assert usage["prompt_tokens"] == 100
    assert usage["estimated_cost"] == 0.01
