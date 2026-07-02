from paper_radar.models import Paper
from paper_radar.paper_notes import PaperNoteService, render_paper_note
from paper_radar.storage import PaperStorage


SUMMARY = {
    "sentence_summary": "提出跨被试 EEG 解码方法。",
    "research_question": "如何提高跨被试泛化？",
    "core_contributions": ["提出新模型", "验证跨被试性能"],
    "method_overview": "使用 Transformer 编码 EEG。",
    "datasets_experiments": "在公开 EEG 数据集上实验。",
    "key_results": "性能优于基线。",
    "research_relevance": "直接相关。",
    "transferable_ideas": ["使用对比预训练"],
    "limitations_questions": "数据规模有限。",
    "tags": ["EEG", "brain_decoding"],
}


class FakeSummarizer:
    def summarize(self, paper, fulltext):
        assert "full text" in fulltext
        return SUMMARY


def make_paper() -> Paper:
    return Paper(
        id="2606.00001",
        title="Cross-subject EEG Decoding",
        authors=["Ada Lovelace"],
        source="arxiv",
        published="2026-06-10",
        url="https://arxiv.org/abs/2606.00001",
        pdf_url="https://arxiv.org/pdf/2606.00001.pdf",
        fetched_at="2026-06-10T10:00:00+08:00",
        llm_score=9,
        llm_decision="read",
    )


def test_render_paper_note_contains_required_sections():
    content = render_paper_note(make_paper(), SUMMARY)
    assert "## 一句话总结" in content
    assert "## 数据集与实验设置" in content
    assert "* [ ] 查代码" in content


def test_paper_note_service_writes_note_and_status(tmp_path):
    storage = PaperStorage(tmp_path / "papers.db")
    paper = make_paper()
    storage.upsert_paper(paper)
    extracted = tmp_path / "extracted.md"
    extracted.write_text("full text", encoding="utf-8")
    storage.update_pdf_extract(paper.id, "extracted", str(extracted))
    paper = storage.get_paper(paper.id)

    service = PaperNoteService(
        storage=storage,
        config={
            "paper_notes_dir": str(tmp_path / "notes"),
            "obsidian_paper_notes_dir": None,
            "max_fulltext_chars_for_llm": 1000,
        },
        summarizer=FakeSummarizer(),
    )
    paths = service.summarize(paper)
    assert paths[0].exists()
    saved = storage.get_paper(paper.id)
    assert saved.full_summary_status == "summarized"
    assert saved.paper_note_path == str(paths[0])
