"""Integration tests for pipeline resume functionality."""

from unittest.mock import patch


from showcase.builder import build_resume_graph
from showcase.models import Analysis, GeneratedContent, create_initial_state


class TestResumeFromAnalyze:
    """Tests for resuming pipeline with existing generated content."""

    @patch("showcase.node_factory.execute_prompt")
    def test_resume_with_generated_skips_generate(self, mock_execute):
        """Should skip generate when generated content exists."""
        # Create state with generated content
        state = create_initial_state(topic="test", thread_id="resume1")
        state["generated"] = GeneratedContent(
            title="Existing Title",
            content="Existing content",
            word_count=10,
            tags=[],
        )
        state["current_step"] = "generate"

        # Mock returns: analyze, summarize (generate is skipped)
        mock_analysis = Analysis(
            summary="Resume summary",
            key_points=["Point"],
            sentiment="neutral",
            confidence=0.7,
        )
        mock_execute.side_effect = [mock_analysis, "Final summary"]

        graph = build_resume_graph().compile()
        result = graph.invoke(state)

        assert mock_execute.call_count == 2  # analyze + summarize only
        assert result["analysis"] == mock_analysis
        assert result["final_summary"] == "Final summary"
        assert result["generated"].title == "Existing Title"  # Preserved


class TestResumeFromSummarize:
    """Tests for resuming pipeline with existing analysis."""

    @patch("showcase.node_factory.execute_prompt")
    def test_resume_with_analysis_skips_generate_and_analyze(self, mock_execute):
        """Should skip generate and analyze when both exist."""
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

        # Mock returns: only summarize (generate and analyze skipped)
        mock_execute.return_value = "Resumed final summary"

        graph = build_resume_graph().compile()
        result = graph.invoke(state)

        assert mock_execute.call_count == 1  # summarize only
        assert result["final_summary"] == "Resumed final summary"
        assert result["generated"].title == "Title"  # Preserved
        assert result["analysis"].summary == "Existing analysis"  # Preserved
