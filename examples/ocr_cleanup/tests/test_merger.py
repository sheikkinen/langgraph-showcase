"""Tests for paragraph merger tool."""

from __future__ import annotations


class TestMergeParagraphs:
    """Tests for merge_paragraphs function."""

    def test_simple_merge_no_spans(self) -> None:
        """Pages with complete paragraphs need no merging."""
        from examples.ocr_cleanup.tools.merger import merge_paragraphs

        cleaned_pages = [
            {
                "page_num": 1,
                "paragraphs": [
                    {
                        "text": "First paragraph.",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": False,
                    },
                    {
                        "text": "Second paragraph.",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": False,
                    },
                ],
                "corrections": [],
            },
            {
                "page_num": 2,
                "paragraphs": [
                    {
                        "text": "Third paragraph.",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": False,
                    },
                ],
                "corrections": [],
            },
        ]

        result = merge_paragraphs(cleaned_pages)

        assert len(result["paragraphs"]) == 3
        assert result["paragraphs"][0]["text"] == "First paragraph."
        assert result["paragraphs"][2]["text"] == "Third paragraph."

    def test_merge_spanning_paragraph(self) -> None:
        """Paragraph spanning pages is merged."""
        from examples.ocr_cleanup.tools.merger import merge_paragraphs

        cleaned_pages = [
            {
                "page_num": 1,
                "paragraphs": [
                    {
                        "text": "Complete paragraph.",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": False,
                    },
                    {
                        "text": "This continues to",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": True,
                    },
                ],
                "corrections": [],
            },
            {
                "page_num": 2,
                "paragraphs": [
                    {
                        "text": "the next page here.",
                        "starts_mid_sentence": True,
                        "ends_mid_sentence": False,
                    },
                    {
                        "text": "New paragraph.",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": False,
                    },
                ],
                "corrections": [],
            },
        ]

        result = merge_paragraphs(cleaned_pages)

        assert len(result["paragraphs"]) == 3
        assert (
            result["paragraphs"][1]["text"] == "This continues to the next page here."
        )
        assert result["paragraphs"][1]["start_page"] == 1
        assert result["paragraphs"][1]["end_page"] == 2

    def test_multi_page_span(self) -> None:
        """Paragraph spanning 3 pages."""
        from examples.ocr_cleanup.tools.merger import merge_paragraphs

        cleaned_pages = [
            {
                "page_num": 1,
                "paragraphs": [
                    {
                        "text": "Start of long",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": True,
                    },
                ],
                "corrections": [],
            },
            {
                "page_num": 2,
                "paragraphs": [
                    {
                        "text": "paragraph that spans",
                        "starts_mid_sentence": True,
                        "ends_mid_sentence": True,
                    },
                ],
                "corrections": [],
            },
            {
                "page_num": 3,
                "paragraphs": [
                    {
                        "text": "three pages.",
                        "starts_mid_sentence": True,
                        "ends_mid_sentence": False,
                    },
                ],
                "corrections": [],
            },
        ]

        result = merge_paragraphs(cleaned_pages)

        assert len(result["paragraphs"]) == 1
        assert (
            result["paragraphs"][0]["text"]
            == "Start of long paragraph that spans three pages."
        )

    def test_corrections_aggregated(self) -> None:
        """All corrections from all pages are collected."""
        from examples.ocr_cleanup.tools.merger import merge_paragraphs

        cleaned_pages = [
            {
                "page_num": 1,
                "paragraphs": [],
                "corrections": [
                    {"original": "a", "corrected": "b", "type": "ocr_char"}
                ],
            },
            {
                "page_num": 2,
                "paragraphs": [],
                "corrections": [
                    {"original": "c", "corrected": "d", "type": "ocr_char"},
                    {"original": "..  .", "corrected": "...", "type": "ellipsis"},
                ],
            },
        ]

        result = merge_paragraphs(cleaned_pages)

        assert len(result["corrections"]) == 3

    def test_chapter_markers_preserved(self) -> None:
        """Chapter starts are tracked in output."""
        from examples.ocr_cleanup.tools.merger import merge_paragraphs

        cleaned_pages = [
            {
                "page_num": 5,
                "paragraphs": [
                    {
                        "text": "Chapter content.",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": False,
                    }
                ],
                "corrections": [],
                "is_chapter_start": True,
                "chapter_title": "I LUKU",
            },
            {
                "page_num": 6,
                "paragraphs": [
                    {
                        "text": "More content.",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": False,
                    }
                ],
                "corrections": [],
                "is_chapter_start": False,
                "chapter_title": None,
            },
        ]

        result = merge_paragraphs(cleaned_pages)

        assert "chapters" in result
        assert len(result["chapters"]) == 1
        assert result["chapters"][0]["title"] == "I LUKU"
        assert result["chapters"][0]["start_page"] == 5

    def test_node_wrapper(self) -> None:
        """Node wrapper extracts from state."""
        from examples.ocr_cleanup.tools.merger import merge_paragraphs_node

        state = {
            "map_results": [
                {
                    "page_num": 1,
                    "paragraphs": [
                        {
                            "text": "Test.",
                            "starts_mid_sentence": False,
                            "ends_mid_sentence": False,
                        }
                    ],
                    "corrections": [],
                }
            ]
        }

        result = merge_paragraphs_node(state)

        assert "paragraphs" in result
        assert "corrections" in result


class TestMergeStats:
    """Tests for statistics generation."""

    def test_stats_included(self) -> None:
        """Output includes statistics."""
        from examples.ocr_cleanup.tools.merger import merge_paragraphs

        cleaned_pages = [
            {
                "page_num": 1,
                "paragraphs": [
                    {
                        "text": "P1.",
                        "starts_mid_sentence": False,
                        "ends_mid_sentence": False,
                    }
                ],
                "corrections": [
                    {"original": "a", "corrected": "b", "type": "ocr_char"},
                    {"original": "c-\nd", "corrected": "cd", "type": "hyphenation"},
                ],
            },
        ]

        result = merge_paragraphs(cleaned_pages)

        assert "stats" in result
        assert result["stats"]["total_paragraphs"] == 1
        assert result["stats"]["total_corrections"] == 2
        assert result["stats"]["corrections_by_type"]["ocr_char"] == 1
        assert result["stats"]["corrections_by_type"]["hyphenation"] == 1
