from paper_radar.chat import format_chat_report, format_paper_detail
from paper_radar.models import Paper


def sample_paper() -> Paper:
    return Paper(
        id="2606.00001",
        title="EEG Decoding with Multimodal Models",
        authors=["Ada"],
        summary="A paper about EEG decoding.",
        source_category="q-bio.NC",
        url="https://arxiv.org/abs/2606.00001",
        pdf_url="https://arxiv.org/pdf/2606.00001.pdf",
        fetched_at="2026-06-08T08:00:00+08:00",
        rule_score=12,
        status="llm_pending",
    )


def test_chat_report_contains_source_links():
    report = format_chat_report("2026-06-08", [sample_paper()], limit=10)
    assert "EEG Decoding" in report
    assert "原文：https://arxiv.org/abs/2606.00001" in report
    assert "PDF：https://arxiv.org/pdf/2606.00001.pdf" in report


def test_paper_detail_contains_abstract():
    detail = format_paper_detail(sample_paper())
    assert "A paper about EEG decoding." in detail
