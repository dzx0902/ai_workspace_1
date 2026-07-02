from paper_radar.models import Paper
from paper_radar.scoring import decision_for_score, score_paper


KEYWORDS = {
    "topics": {
        "brain_signals": {"high": ["EEG"], "medium": ["brain signal"]},
        "ai_sota": {"high": ["RAG"], "medium": []},
    }
}
SCORING = {
    "weights": {
        "title": {"high": 6, "medium": 3},
        "abstract": {"high": 3, "medium": 1},
    }
}


def test_scoring_matches_case_insensitively_in_both_fields():
    paper = Paper(
        id="1",
        title="EEG foundation models",
        summary="We study eeg as a brain signal.",
    )
    result = score_paper(paper, KEYWORDS, SCORING)
    assert result.score == 10
    assert {(match["field"], match["keyword"]) for match in result.matches} == {
        ("title", "EEG"),
        ("abstract", "EEG"),
        ("abstract", "brain signal"),
    }


def test_short_keyword_uses_word_boundaries():
    paper = Paper(id="2", title="Drag-based interaction", summary="No retrieval system.")
    result = score_paper(paper, KEYWORDS, SCORING)
    assert result.score == 0


def test_decision_ranges_control_final_decision():
    config = {
        "decision_ranges": {
            "read": {"min": 8, "max": 10},
            "skim": {"min": 5, "max": 7},
            "skip": {"min": 0, "max": 4},
        }
    }
    assert decision_for_score(8, config) == "read"
    assert decision_for_score(6.5, config) == "skim"
    assert decision_for_score(2, config) == "skip"
