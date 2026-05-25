from __future__ import annotations
import pytest
from src.commentary import validate_commentary, CommentaryError


def _valid_payload():
    return {
        "changes": [
            {"index": 0, "so_what": "x", "tag": "Threat", "confidence": 0.9},
        ],
        "synthesis": {
            "themes": ["t"], "watch_list": ["w"],
            "suggested_response": "r", "prior_watchlist_status": [],
        },
    }


def test_validate_accepts_good_payload():
    out = validate_commentary(_valid_payload(), n_changes=1)
    assert out["changes"][0]["tag"] == "Threat"


def test_validate_rejects_bad_tag():
    bad = _valid_payload()
    bad["changes"][0]["tag"] = "Spicy"
    with pytest.raises(CommentaryError, match="tag"):
        validate_commentary(bad, n_changes=1)


def test_validate_rejects_confidence_out_of_range():
    bad = _valid_payload()
    bad["changes"][0]["confidence"] = 1.5
    with pytest.raises(CommentaryError, match="confidence"):
        validate_commentary(bad, n_changes=1)


def test_validate_rejects_change_count_mismatch():
    with pytest.raises(CommentaryError, match="count"):
        validate_commentary(_valid_payload(), n_changes=2)
