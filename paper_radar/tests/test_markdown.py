from paper_radar.markdown import render_daily_note, write_daily_note
from paper_radar.models import Paper


def test_render_no_llm_note_and_write_local_copy(tmp_path):
    paper = Paper(
        id="1",
        title="EEG Decoding",
        url="https://arxiv.org/abs/1",
        pdf_url="https://arxiv.org/pdf/1.pdf",
        fetched_at="2026-06-08T10:00:00+08:00",
        rule_score=12,
        matched_keywords=[{"topic": "brain_signals", "keyword": "EEG"}],
        status="llm_pending",
    )
    content = render_daily_note(
        "2026-06-08",
        [paper],
        no_llm=True,
        scoring_config={"llm_min_rule_score": 4},
    )
    assert "未执行 LLM 评分" in content
    assert "## 强相关，建议精读" in content
    assert "https://arxiv.org/pdf/1.pdf" in content

    paths = write_daily_note(
        "2026-06-08",
        content,
        {
            "daily_filename_format": "%Y-%m-%d-paper-radar.md",
            "write_local_copy": True,
            "local_output_dir": str(tmp_path),
            "obsidian_output_dir": None,
        },
    )
    assert paths[0].read_text(encoding="utf-8") == content
