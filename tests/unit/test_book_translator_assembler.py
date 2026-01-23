"""Unit tests for book translator assembler node."""

import sys
from pathlib import Path

# Add examples to path for testing
examples_path = Path(__file__).parent.parent.parent / "examples" / "book_translator"
sys.path.insert(0, str(examples_path))

from nodes.tools import join_chunks  # noqa: E402


class TestJoinChunks:
    """Tests for chunk reassembly."""

    def test_empty_state(self):
        """Handle empty state gracefully."""
        state = {}
        result = join_chunks(state)

        assert "final_text" in result
        assert result["final_text"] == ""

    def test_join_proofread_chunks(self):
        """Join corrected text from proofread chunks (map node output format)."""
        state = {
            "proofread_chunks": [
                {"_map_proofread_all_sub": {"corrected_text": "Chapter 1 translated."}},
                {"_map_proofread_all_sub": {"corrected_text": "Chapter 2 translated."}},
                {"_map_proofread_all_sub": {"corrected_text": "Chapter 3 translated."}},
            ],
        }
        result = join_chunks(state)

        assert "Chapter 1 translated." in result["final_text"]
        assert "Chapter 2 translated." in result["final_text"]
        assert "Chapter 3 translated." in result["final_text"]

    def test_human_reviewed_chunks_override(self):
        """Human-reviewed chunks take priority."""
        state = {
            "proofread_chunks": [
                {"_map_proofread_all_sub": {"corrected_text": "Auto translation."}},
                {"_map_proofread_all_sub": {"corrected_text": "Auto translation 2."}},
            ],
            "reviewed_chunks": {
                "0": "Human corrected translation.",
            },
        }
        result = join_chunks(state)

        assert "Human corrected translation." in result["final_text"]
        assert "Auto translation 2." in result["final_text"]
        assert "Auto translation." not in result["final_text"]

    def test_chunks_joined_with_double_newline(self):
        """Chunks should be joined with double newline."""
        state = {
            "proofread_chunks": [
                {"_map_proofread_all_sub": {"corrected_text": "Part 1"}},
                {"_map_proofread_all_sub": {"corrected_text": "Part 2"}},
            ],
        }
        result = join_chunks(state)

        assert result["final_text"] == "Part 1\n\nPart 2"

    def test_empty_proofread_chunks(self):
        """Handle empty proofread_chunks list."""
        state = {"proofread_chunks": []}
        result = join_chunks(state)

        assert result["final_text"] == ""

    def test_reviewed_chunks_with_string_keys(self):
        """Human review uses string keys for chunk indices."""
        state = {
            "proofread_chunks": [
                {"_map_proofread_all_sub": {"corrected_text": "Auto 0."}},
                {"_map_proofread_all_sub": {"corrected_text": "Auto 1."}},
            ],
            "reviewed_chunks": {
                "1": "Human 1.",  # String key
            },
        }
        result = join_chunks(state)

        assert "Auto 0." in result["final_text"]
        assert "Human 1." in result["final_text"]
        assert "Auto 1." not in result["final_text"]
