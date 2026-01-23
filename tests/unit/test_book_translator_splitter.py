"""Unit tests for book translator splitter function."""

import sys
from pathlib import Path

# Add examples to path for testing
examples_path = Path(__file__).parent.parent.parent / "examples" / "book_translator"
sys.path.insert(0, str(examples_path))

from nodes.tools import split_by_markers  # noqa: E402


class TestSplitByMarkers:
    """Tests for marker-based text splitting."""

    def test_empty_state(self):
        """Handle empty state gracefully."""
        state = {}
        result = split_by_markers(state)

        assert "chunks" in result
        assert result["chunks"] == []  # No text = no chunks

    def test_no_markers(self):
        """Return full document when no markers found."""
        state = {
            "source_text": "This is some text without any markers.",
            "chapter_markers": {"markers": []},
        }
        result = split_by_markers(state)

        assert len(result["chunks"]) == 1
        assert result["chunks"][0]["title"] == "Full Document"

    def test_split_with_markers(self):
        """Split text at marker positions."""
        text = """Introduction to the book.

Chapter 1: The Beginning
This is chapter one content.

Chapter 2: The Middle
This is chapter two content."""

        # Mock ChapterMarkers-like structure
        state = {
            "source_text": text,
            "chapter_markers": {
                "markers": [
                    {"marker": "Chapter 1: The Beginning", "title": "The Beginning"},
                    {"marker": "Chapter 2: The Middle", "title": "The Middle"},
                ]
            },
        }
        result = split_by_markers(state)

        assert len(result["chunks"]) == 3
        assert result["chunks"][0]["title"] == "Introduction"
        assert result["chunks"][1]["title"] == "The Beginning"
        assert result["chunks"][2]["title"] == "The Middle"

    def test_chunks_have_context(self):
        """Chunks should include context from adjacent sections."""
        text = """Intro content here.

SECTION A
Content of section A here.

SECTION B
Content of section B here."""

        state = {
            "source_text": text,
            "chapter_markers": {
                "markers": [
                    {"marker": "SECTION A", "title": "Section A"},
                    {"marker": "SECTION B", "title": "Section B"},
                ]
            },
        }
        result = split_by_markers(state, context_chars=50)

        # Check that chunks have context fields
        for chunk in result["chunks"]:
            assert "context_before" in chunk
            assert "context_after" in chunk

    def test_chunk_indices_are_sequential(self):
        """Chunk indices should be 0, 1, 2, etc."""
        text = "Part A\n\nPart B\n\nPart C"
        state = {
            "source_text": text,
            "chapter_markers": {
                "markers": [
                    {"marker": "Part B", "title": "B"},
                    {"marker": "Part C", "title": "C"},
                ]
            },
        }
        result = split_by_markers(state)

        for i, chunk in enumerate(result["chunks"]):
            assert chunk["index"] == i

    def test_handles_pydantic_model(self):
        """Handle Pydantic ChapterMarkers model."""
        from dataclasses import dataclass

        @dataclass
        class MockMarker:
            marker: str
            title: str

        @dataclass
        class MockChapterMarkers:
            markers: list

        state = {
            "source_text": "Intro\n\nChapter 1\nContent",
            "chapter_markers": MockChapterMarkers(
                markers=[MockMarker(marker="Chapter 1", title="Ch 1")]
            ),
        }
        result = split_by_markers(state)

        assert len(result["chunks"]) >= 1
