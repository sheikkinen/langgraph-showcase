"""Unit tests for book translator quality check function."""

import sys
from pathlib import Path

import pytest

# Add examples to path for testing
examples_path = Path(__file__).parent.parent.parent / "examples" / "book_translator"
sys.path.insert(0, str(examples_path))

from nodes.tools import check_scores  # noqa: E402


class TestCheckScores:
    """Tests for quality score checking."""

    @pytest.mark.req("REQ-YG-014")
    def test_empty_state(self):
        """Handle empty state gracefully."""
        state = {}
        result = check_scores(state)

        assert "flagged_chunks" in result
        assert "needs_review" in result
        assert result["flagged_chunks"] == []
        assert result["needs_review"] is False

    @pytest.mark.req("REQ-YG-014")
    def test_all_chunks_pass(self):
        """No flags when all chunks pass threshold."""
        state = {
            "proofread_chunks": [
                {
                    "_map_proofread_all_sub": {
                        "quality_score": 0.95,
                        "approved": True,
                    }
                },
                {
                    "_map_proofread_all_sub": {
                        "quality_score": 0.88,
                        "approved": True,
                    }
                },
            ],
        }
        result = check_scores(state, threshold=0.8)

        assert len(result["flagged_chunks"]) == 0
        assert result["needs_review"] is False

    @pytest.mark.req("REQ-YG-014")
    def test_flag_low_score_chunks(self):
        """Flag chunks with scores below threshold."""
        state = {
            "proofread_chunks": [
                {
                    "_map_proofread_all_sub": {
                        "quality_score": 0.95,
                        "approved": True,
                    }
                },
                {
                    "_map_proofread_all_sub": {
                        "quality_score": 0.65,
                        "approved": False,
                    }
                },
                {
                    "_map_proofread_all_sub": {
                        "quality_score": 0.55,
                        "approved": False,
                    }
                },
            ],
        }
        result = check_scores(state, threshold=0.8)

        assert len(result["flagged_chunks"]) == 2
        assert result["needs_review"] is True
        # Check flagged chunk indices
        flagged_indices = [f["index"] for f in result["flagged_chunks"]]
        assert 1 in flagged_indices
        assert 2 in flagged_indices

    @pytest.mark.req("REQ-YG-014")
    def test_flag_not_approved_chunks(self):
        """Flag chunks that are not approved even if score is above threshold."""
        state = {
            "proofread_chunks": [
                {
                    "_map_proofread_all_sub": {
                        "quality_score": 0.90,
                        "approved": False,  # Not approved despite good score
                    }
                },
            ],
        }
        result = check_scores(state, threshold=0.8)

        assert len(result["flagged_chunks"]) == 1
        assert result["needs_review"] is True

    @pytest.mark.req("REQ-YG-014")
    def test_custom_threshold(self):
        """Use custom threshold for flagging."""
        state = {
            "proofread_chunks": [
                {
                    "_map_proofread_all_sub": {
                        "quality_score": 0.85,
                        "approved": True,
                    }
                },
            ],
        }

        # With 0.8 threshold, should pass
        result_low = check_scores(state, threshold=0.8)
        assert len(result_low["flagged_chunks"]) == 0

        # With 0.9 threshold, should fail
        result_high = check_scores(state, threshold=0.9)
        assert len(result_high["flagged_chunks"]) == 1

    @pytest.mark.req("REQ-YG-014")
    def test_handle_missing_scores(self):
        """Handle chunks without quality_score field - defaults to 1.0."""
        state = {
            "proofread_chunks": [
                {
                    "_map_proofread_all_sub": {"approved": True}
                },  # No score defaults to 1.0
                {
                    "_map_proofread_all_sub": {
                        "quality_score": 0.95,
                        "approved": True,
                    }
                },
            ],
        }
        result = check_scores(state, threshold=0.8)

        # Chunk without score defaults to 1.0 and passes
        assert len(result["flagged_chunks"]) == 0

    @pytest.mark.req("REQ-YG-014")
    def test_handle_pydantic_model(self):
        """Handle Pydantic ProofreadOutput model."""
        from dataclasses import dataclass

        @dataclass
        class MockProofreadOutput:
            quality_score: float
            approved: bool

        state = {
            "proofread_chunks": [
                {"_map_proofread_all_sub": MockProofreadOutput(0.95, True)},
                {"_map_proofread_all_sub": MockProofreadOutput(0.65, False)},
            ],
        }
        result = check_scores(state, threshold=0.8)

        assert len(result["flagged_chunks"]) == 1
        assert result["flagged_chunks"][0]["index"] == 1
