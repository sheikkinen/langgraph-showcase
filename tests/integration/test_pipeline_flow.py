"""Integration tests for the complete pipeline flow."""

from unittest.mock import patch

import pytest

from showcase.builder import build_resume_graph, build_showcase_graph, run_pipeline
from tests.conftest import FixtureAnalysis, FixtureGeneratedContent


class TestBuildShowcaseGraph:
    """Tests for build_showcase_graph function."""

    def test_graph_compiles(self):
        """Graph should compile without errors."""
        graph = build_showcase_graph()
        compiled = graph.compile()
        assert compiled is not None

    def test_graph_has_expected_nodes(self):
        """Graph should have generate, analyze, summarize nodes."""
        graph = build_showcase_graph()
        # StateGraph stores nodes internally
        assert "generate" in graph.nodes
        assert "analyze" in graph.nodes
        assert "summarize" in graph.nodes


class TestBuildResumeGraph:
    """Tests for build_resume_graph function.

    Resume works via skip_if_exists: nodes skip LLM calls if output exists in state.
    """

    def test_resume_graph_loads_full_pipeline(self):
        """Resume graph loads the full pipeline (same as main graph)."""
        graph = build_resume_graph()
        # All nodes present - skip_if_exists handles resume logic
        assert "generate" in graph.nodes
        assert "analyze" in graph.nodes
        assert "summarize" in graph.nodes

    def test_resume_graph_same_as_main(self):
        """Resume graph is identical to main showcase graph."""
        main_graph = build_showcase_graph()
        resume_graph = build_resume_graph()

        assert set(main_graph.nodes.keys()) == set(resume_graph.nodes.keys())


class TestRunPipeline:
    """Tests for run_pipeline function with mocked LLM."""

    @patch("showcase.node_factory.execute_prompt")
    def test_full_pipeline_success(self, mock_execute):
        """Full pipeline should execute all steps."""
        # Setup mock returns for each call
        mock_generated = FixtureGeneratedContent(
            title="Test Title",
            content="Test content " * 50,
            word_count=100,
            tags=["test"],
        )
        mock_analysis = FixtureAnalysis(
            summary="Test summary",
            key_points=["Point 1"],
            sentiment="positive",
            confidence=0.9,
        )
        mock_summary = "Final test summary"

        mock_execute.side_effect = [mock_generated, mock_analysis, mock_summary]

        result = run_pipeline(topic="test", style="informative", word_count=100)

        assert result["generated"] == mock_generated
        assert result["analysis"] == mock_analysis
        assert result["final_summary"] == mock_summary
        assert mock_execute.call_count == 3

    @patch("showcase.node_factory.execute_prompt")
    def test_pipeline_stops_on_generate_error(self, mock_execute):
        """Pipeline should stop and raise exception on generate failure."""
        mock_execute.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            run_pipeline(topic="test")

        assert "API Error" in str(exc_info.value)

    @patch("showcase.node_factory.execute_prompt")
    def test_pipeline_state_progression(self, mock_execute):
        """Pipeline should update current_step as it progresses."""
        mock_generated = FixtureGeneratedContent(
            title="Test", content="Content", word_count=1, tags=[]
        )
        mock_analysis = FixtureAnalysis(
            summary="Summary", key_points=[], sentiment="neutral", confidence=0.5
        )
        mock_execute.side_effect = [mock_generated, mock_analysis, "Summary"]

        result = run_pipeline(topic="test")

        # Final step should be summarize
        assert result["current_step"] == "summarize"
