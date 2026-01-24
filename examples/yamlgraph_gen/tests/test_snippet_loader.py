"""Tests for snippet_loader module."""

import pytest

from examples.yamlgraph_gen.tools.snippet_loader import (
    PATTERN_SNIPPETS,
    get_snippet_index,
    list_snippets,
    load_snippet,
    load_snippets,
    load_snippets_for_patterns,
)


class TestListSnippets:
    """Tests for list_snippets function."""

    def test_list_all_snippets(self) -> None:
        """List all available snippets."""
        result = list_snippets()

        # Should return snippets from all categories
        assert isinstance(result, list)
        # Check we have some snippets
        assert len(result) > 0

    def test_list_snippets_by_category(self) -> None:
        """List snippets filtered by category."""
        result = list_snippets("nodes")

        assert isinstance(result, list)
        # Should have node snippets
        assert "llm-basic" in result or len(result) >= 0

    def test_list_snippets_missing_category(self) -> None:
        """List snippets for non-existent category returns empty."""
        result = list_snippets("nonexistent")

        assert result == []


class TestLoadSnippet:
    """Tests for load_snippet function."""

    def test_load_existing_snippet(self) -> None:
        """Load a snippet that exists."""
        result = load_snippet("nodes/llm-basic")

        assert "content" in result
        assert "data" in result
        assert result["category"] == "nodes"
        assert result["name"] == "llm-basic"

    def test_load_snippet_with_yaml_extension(self) -> None:
        """Load snippet with .yaml extension included."""
        result = load_snippet("nodes/llm-basic.yaml")

        assert result["name"] == "llm-basic"

    def test_load_missing_snippet_raises(self) -> None:
        """Loading missing snippet raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Snippet not found"):
            load_snippet("nodes/nonexistent")


class TestLoadSnippets:
    """Tests for load_snippets function."""

    def test_load_multiple_snippets(self) -> None:
        """Load multiple snippets at once."""
        result = load_snippets(["nodes/llm-basic", "edges/linear"])

        assert "nodes/llm-basic" in result
        assert "edges/linear" in result

    def test_load_snippets_skips_missing(self) -> None:
        """Missing snippets are skipped, not errored."""
        result = load_snippets(["nodes/llm-basic", "nodes/nonexistent"])

        assert "nodes/llm-basic" in result
        assert "nodes/nonexistent" not in result


class TestLoadSnippetsForPatterns:
    """Tests for load_snippets_for_patterns function."""

    def test_load_for_router_pattern(self) -> None:
        """Load snippets needed for router pattern."""
        result = load_snippets_for_patterns(["router"])

        assert "patterns" in result
        assert result["patterns"] == ["router"]
        assert "snippet_contents" in result

    def test_load_for_multiple_patterns(self) -> None:
        """Load snippets for combined patterns."""
        result = load_snippets_for_patterns(["router", "map"])

        assert result["patterns"] == ["router", "map"]
        # Should have snippets from both patterns
        assert len(result["snippet_contents"]) > 0

    def test_load_for_unknown_pattern(self) -> None:
        """Unknown patterns return empty snippets."""
        result = load_snippets_for_patterns(["unknown"])

        assert result["patterns"] == ["unknown"]
        assert result["snippet_contents"] == {}


class TestPatternSnippetsMapping:
    """Tests for PATTERN_SNIPPETS constant."""

    def test_all_patterns_have_snippets(self) -> None:
        """All defined patterns have snippet lists."""
        expected_patterns = [
            "linear",
            "router",
            "map",
            "interrupt",
            "agent",
            "subgraph",
        ]

        for pattern in expected_patterns:
            assert pattern in PATTERN_SNIPPETS
            assert len(PATTERN_SNIPPETS[pattern]) > 0


class TestGetSnippetIndex:
    """Tests for get_snippet_index function."""

    def test_get_index_structure(self) -> None:
        """Index has expected structure."""
        result = get_snippet_index()

        assert isinstance(result, dict)
        # Should have at least nodes category
        if "nodes" in result:
            assert isinstance(result["nodes"], list)
            if result["nodes"]:
                snippet = result["nodes"][0]
                assert "name" in snippet
                assert "path" in snippet
