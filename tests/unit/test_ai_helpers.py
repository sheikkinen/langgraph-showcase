"""Tests for AI helper tools (context compression, diff preview, similarity)."""

from yamlgraph.tools.analysis.ai_helpers import (
    diff_preview,
    find_similar_code,
    summarize_module,
)


class TestSummarizeModule:
    """Tests for summarize_module function."""

    def test_summarizes_real_module(self):
        """Summarizes a real module with classes and functions."""
        result = summarize_module("yamlgraph/executor.py")

        assert "error" not in result
        assert "summary" in result
        assert isinstance(result["summary"], str)
        # Should be significantly shorter than original file
        assert len(result["summary"]) < 2000

    def test_includes_class_names(self):
        """Summary includes class names."""
        result = summarize_module("yamlgraph/models/schemas.py")

        assert "error" not in result
        # Should mention key classes
        assert "class" in result["summary"].lower() or "Class" in result["summary"]

    def test_includes_function_signatures(self):
        """Summary includes function signatures (not bodies)."""
        result = summarize_module("yamlgraph/executor.py")

        assert "error" not in result
        # Should have function defs
        assert "def " in result["summary"]
        # Bodies are stripped - should be much shorter than reading whole file

    def test_includes_docstring(self):
        """Summary includes module docstring."""
        result = summarize_module("yamlgraph/executor.py")

        assert "error" not in result
        # Module docstring should be preserved
        assert len(result["summary"]) > 50  # Not empty

    def test_returns_error_for_invalid_file(self):
        """Returns error for non-existent file."""
        result = summarize_module("nonexistent/file.py")

        assert "error" in result

    def test_max_length_parameter(self):
        """Respects max_length parameter."""
        result = summarize_module("yamlgraph/executor.py", max_length=500)

        assert "error" not in result
        assert len(result["summary"]) <= 550  # Some tolerance

    def test_returns_line_count(self):
        """Returns original line count for context."""
        result = summarize_module("yamlgraph/executor.py")

        assert "error" not in result
        assert "original_lines" in result
        assert result["original_lines"] > 50


class TestDiffPreview:
    """Tests for diff_preview function."""

    def test_shows_add_diff(self):
        """Shows diff for adding a line."""
        result = diff_preview(
            file_path="yamlgraph/__init__.py",
            line=1,
            action="ADD",
            new_code="# New comment",
        )

        assert "error" not in result
        assert "diff" in result
        assert "+" in result["diff"]  # Added line marker

    def test_shows_modify_diff(self):
        """Shows diff for modifying a line."""
        # Read first line to modify it
        result = diff_preview(
            file_path="yamlgraph/__init__.py",
            line=1,
            action="MODIFY",
            new_code='"""Modified docstring."""',
        )

        assert "error" not in result
        assert "diff" in result
        # Should show both old (-) and new (+)

    def test_shows_delete_diff(self):
        """Shows diff for deleting a line."""
        result = diff_preview(
            file_path="yamlgraph/__init__.py",
            line=1,
            action="DELETE",
            new_code="",
        )

        assert "error" not in result
        assert "diff" in result
        assert "-" in result["diff"]  # Deleted line marker

    def test_returns_error_for_invalid_file(self):
        """Returns error for non-existent file."""
        result = diff_preview(
            file_path="nonexistent/file.py",
            line=1,
            action="ADD",
            new_code="test",
        )

        assert "error" in result

    def test_returns_error_for_invalid_line(self):
        """Returns error for line beyond file length."""
        result = diff_preview(
            file_path="yamlgraph/__init__.py",
            line=99999,
            action="MODIFY",
            new_code="test",
        )

        assert "error" in result

    def test_validates_syntax_of_result(self):
        """Optionally validates syntax of resulting code."""
        result = diff_preview(
            file_path="yamlgraph/__init__.py",
            line=1,
            action="MODIFY",
            new_code="def broken(:",  # Invalid syntax - colon after open paren
            validate_syntax=True,
        )

        # Should still return diff but flag syntax issue
        assert "syntax_valid" in result
        assert result["syntax_valid"] is False


class TestFindSimilarCode:
    """Tests for find_similar_code function."""

    def test_finds_similar_functions(self):
        """Finds functions with similar structure."""
        # Look for functions similar to git_blame (simple tool pattern)
        result = find_similar_code(
            file_path="yamlgraph/tools/analysis/git_tools.py",
            symbol_name="git_blame",
            project_path="yamlgraph/tools/analysis",
        )

        assert "error" not in result
        assert "similar" in result
        assert isinstance(result["similar"], list)

    def test_returns_file_and_line(self):
        """Each result includes file and line."""
        result = find_similar_code(
            file_path="yamlgraph/tools/analysis/git_tools.py",
            symbol_name="git_blame",
            project_path="yamlgraph/tools/analysis",
        )

        assert "error" not in result
        for item in result["similar"]:
            assert "file" in item
            assert "name" in item
            assert "line" in item

    def test_includes_similarity_reason(self):
        """Results explain why they're similar."""
        result = find_similar_code(
            file_path="yamlgraph/tools/analysis/git_tools.py",
            symbol_name="git_blame",
            project_path="yamlgraph/tools/analysis",
        )

        assert "error" not in result
        for item in result["similar"]:
            assert "reason" in item

    def test_returns_error_for_invalid_file(self):
        """Returns error for non-existent file."""
        result = find_similar_code(
            file_path="nonexistent/file.py",
            symbol_name="foo",
            project_path="yamlgraph",
        )

        assert "error" in result

    def test_returns_error_for_invalid_symbol(self):
        """Returns error for non-existent symbol."""
        result = find_similar_code(
            file_path="yamlgraph/executor.py",
            symbol_name="nonexistent_function_xyz",
            project_path="yamlgraph",
        )

        assert "error" in result

    def test_max_results_parameter(self):
        """Respects max_results parameter."""
        result = find_similar_code(
            file_path="yamlgraph/tools/analysis/git_tools.py",
            symbol_name="git_blame",
            project_path="yamlgraph/tools/analysis",
            max_results=2,
        )

        assert "error" not in result
        assert len(result["similar"]) <= 2

    def test_includes_code_snippet(self):
        """Results include code snippet."""
        result = find_similar_code(
            file_path="yamlgraph/tools/analysis/git_tools.py",
            symbol_name="git_blame",
            project_path="yamlgraph/tools/analysis",
        )

        assert "error" not in result
        for item in result["similar"]:
            assert "snippet" in item
            assert "def " in item["snippet"]
