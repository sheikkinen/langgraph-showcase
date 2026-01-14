"""Integration tests for pipeline resume functionality."""

from unittest.mock import patch

import pytest

from showcase.builder import build_resume_graph
from showcase.models import Analysis, GeneratedContent, create_initial_state


class TestResumeFromAnalyze:
    """Tests for resuming pipeline from analyze step."""

    @patch("showcase.graph_loader.execute_prompt")
    def test_resume_from_analyze(self, mock_execute):
        """Should resume from analyze with existing generated content."""
        # Create state with generated content
        state = create_initial_state(topic="test", thread_id="resume1")
        state["generated"] = GeneratedContent(
            title="Existing Title",
            content="Existing content",
            word_count=10,
            tags=[],
        )
        state["current_step"] = "generate"
        
        # Mock returns: generate (overwrites), analyze, summarize
        mock_generated = GeneratedContent(
            title="New Title",
            content="New content",
            word_count=20,
            tags=[],
        )
        mock_analysis = Analysis(
            summary="Resume summary",
            key_points=["Point"],
            sentiment="neutral",
            confidence=0.7,
        )
        mock_execute.side_effect = [mock_generated, mock_analysis, "Final summary"]
        
        graph = build_resume_graph(start_from="analyze").compile()
        result = graph.invoke(state)
        
        assert result["analysis"] == mock_analysis
        assert result["final_summary"] == "Final summary"


class TestResumeFromSummarize:
    """Tests for resuming pipeline from summarize step."""

    @patch("showcase.graph_loader.execute_prompt")
    def test_resume_from_summarize(self, mock_execute):
        """Should resume from summarize with existing analysis."""
        # Create state with generated content and analysis
        state = create_initial_state(topic="test", thread_id="resume2")
        state["generated"] = GeneratedContent(
            title="Title",
            content="Content",
            word_count=5,
            tags=[],
        )
        state["analysis"] = Analysis(
            summary="Existing analysis",
            key_points=["Point"],
            sentiment="positive",
            confidence=0.8,
        )
        state["current_step"] = "analyze"
        
        # Mock returns: generate (overwrites), analyze (overwrites), summarize
        mock_generated = GeneratedContent(
            title="New Title",
            content="New content",
            word_count=20,
            tags=[],
        )
        mock_analysis = Analysis(
            summary="New analysis",
            key_points=["Point"],
            sentiment="neutral",
            confidence=0.7,
        )
        mock_execute.side_effect = [mock_generated, mock_analysis, "Resumed final summary"]
        
        graph = build_resume_graph(start_from="summarize").compile()
        result = graph.invoke(state)
        
        assert result["final_summary"] == "Resumed final summary"
