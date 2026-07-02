import pytest

from paper_radar.llm.router import _extract_json, validate_result


def valid_result():
    return {
        "relevance_score": 8,
        "category": ["brain_signal"],
        "decision": "read",
        "reason": "直接研究 EEG 解码。",
        "keywords": ["EEG"],
        "note_priority": "high",
    }


def test_extracts_fenced_json():
    result = _extract_json('```json\n{"relevance_score": 8}\n```')
    assert result["relevance_score"] == 8


def test_validates_result_enums():
    result = validate_result(valid_result())
    assert result["decision"] == "read"

    invalid = valid_result()
    invalid["decision"] = "later"
    with pytest.raises(ValueError):
        validate_result(invalid)
