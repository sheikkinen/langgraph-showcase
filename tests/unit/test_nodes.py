"""Tests for showcase.nodes.content module."""

from unittest.mock import patch, MagicMock

import pytest

from showcase.nodes.content import (
    generate_node,
    analyze_node,
    summarize_node,
    should_continue,
)
from showcase.models import Analysis, GeneratedContent, create_initial_state


class TestShouldContinue:
    """Tests for should_continue function."""

    def test_continue_with_generated_content(self, sample_state):
        """Should return 'continue' when content is generated."""
        result = should_continue(sample_state)
        assert result == "continue"

    def test_end_on_error(self, empty_state):
        """Should return 'end' when there's an error."""
        empty_state["error"] = "Some error"
        result = should_continue(empty_state)
        assert result == "end"

    def test_end_when_no_content(self, empty_state):
        """Should return 'end' when no content generated."""
        result = should_continue(empty_state)
        assert result == "end"


class TestGenerateNode:
    """Tests for generate_node function."""

    @patch("showcase.nodes.content.execute_prompt")
    def test_generate_success(self, mock_execute, empty_state, sample_generated_content):
        """Generate node should return generated content."""
        mock_execute.return_value = sample_generated_content
        
        result = generate_node(empty_state)
        
        assert "generated" in result
        assert result["generated"] == sample_generated_content
        assert result["current_step"] == "generate"

    @patch("showcase.nodes.content.execute_prompt")
    def test_generate_error_handling(self, mock_execute, empty_state):
        """Generate node should handle errors gracefully."""
        mock_execute.side_effect = Exception("API Error")
        
        result = generate_node(empty_state)
        
        assert "error" in result
        assert "API Error" in result["error"].message
        assert result["current_step"] == "generate"


class TestAnalyzeNode:
    """Tests for analyze_node function."""

    @patch("showcase.nodes.content.execute_prompt")
    def test_analyze_success(self, mock_execute, sample_state, sample_analysis):
        """Analyze node should return analysis."""
        mock_execute.return_value = sample_analysis
        
        result = analyze_node(sample_state)
        
        assert "analysis" in result
        assert result["analysis"] == sample_analysis
        assert result["current_step"] == "analyze"

    def test_analyze_without_content(self, empty_state):
        """Analyze node should error without generated content."""
        result = analyze_node(empty_state)
        
        assert "error" in result
        assert result["error"].message == "No content to analyze"
        assert result["error"].node == "analyze"

    @patch("showcase.nodes.content.execute_prompt")
    def test_analyze_error_handling(self, mock_execute, sample_state):
        """Analyze node should handle errors gracefully."""
        mock_execute.side_effect = Exception("API Error")
        
        result = analyze_node(sample_state)
        
        assert "error" in result
        assert "API Error" in result["error"].message


class TestSummarizeNode:
    """Tests for summarize_node function."""

    @patch("showcase.nodes.content.execute_prompt")
    def test_summarize_success(self, mock_execute, sample_state):
        """Summarize node should return summary."""
        mock_execute.return_value = "Final summary text"
        
        result = summarize_node(sample_state)
        
        assert "final_summary" in result
        assert result["final_summary"] == "Final summary text"
        assert result["current_step"] == "summarize"

    def test_summarize_without_generated(self, empty_state):
        """Summarize node should error without generated content."""
        result = summarize_node(empty_state)
        
        assert "error" in result
        assert "Missing data" in result["error"].message

    def test_summarize_without_analysis(self, sample_state):
        """Summarize node should error without analysis."""
        sample_state["analysis"] = None
        
        result = summarize_node(sample_state)
        
        assert "error" in result
        assert "Missing data" in result["error"].message

    @patch("showcase.nodes.content.execute_prompt")
    def test_summarize_error_handling(self, mock_execute, sample_state):
        """Summarize node should handle errors gracefully."""
        mock_execute.side_effect = Exception("API Error")
        
        result = summarize_node(sample_state)
        
        assert "error" in result
        assert "API Error" in result["error"].message
