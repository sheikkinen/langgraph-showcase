"""Integration tests for the complete pipeline flow."""

from unittest.mock import patch, MagicMock

import pytest

from showcase.builder import build_showcase_graph, build_resume_graph, run_pipeline
from showcase.models import Analysis, GeneratedContent, create_initial_state


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
    """Tests for build_resume_graph function."""

    def test_resume_from_analyze(self):
        """Resume graph from analyze loads full graph."""
        graph = build_resume_graph(start_from="analyze")
        # Now loads full graph - all nodes present
        assert "generate" in graph.nodes
        assert "analyze" in graph.nodes
        assert "summarize" in graph.nodes

    def test_resume_from_summarize(self):
        """Resume graph from summarize loads full graph."""
        graph = build_resume_graph(start_from="summarize")
        # Now loads full graph
        assert "generate" in graph.nodes
        assert "analyze" in graph.nodes
        assert "summarize" in graph.nodes

    def test_resume_invalid_start_raises_error(self):
        """Resume graph should raise ValueError for invalid start_from."""
        with pytest.raises(ValueError, match="start_from must be one of"):
            build_resume_graph(start_from="invalid_node")
        
        with pytest.raises(ValueError, match="start_from must be one of"):
            build_resume_graph(start_from="generate")  # Can't resume from start


class TestRunPipeline:
    """Tests for run_pipeline function with mocked LLM."""

    @patch("showcase.graph_loader.execute_prompt")
    def test_full_pipeline_success(self, mock_execute):
        """Full pipeline should execute all steps."""
        # Setup mock returns for each call
        mock_generated = GeneratedContent(
            title="Test Title",
            content="Test content " * 50,
            word_count=100,
            tags=["test"],
        )
        mock_analysis = Analysis(
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

    @patch("showcase.graph_loader.execute_prompt")
    def test_pipeline_stops_on_generate_error(self, mock_execute):
        """Pipeline should stop and set error on generate failure."""
        mock_execute.side_effect = Exception("API Error")
        
        result = run_pipeline(topic="test")
        
        assert result.get("error") is not None
        assert "API Error" in result["error"].message
        assert result.get("analysis") is None
        assert result.get("final_summary") is None

    @patch("showcase.graph_loader.execute_prompt")
    def test_pipeline_state_progression(self, mock_execute):
        """Pipeline should update current_step as it progresses."""
        mock_generated = GeneratedContent(
            title="Test", content="Content", word_count=1, tags=[]
        )
        mock_analysis = Analysis(
            summary="Summary", key_points=[], sentiment="neutral", confidence=0.5
        )
        mock_execute.side_effect = [mock_generated, mock_analysis, "Summary"]
        
        result = run_pipeline(topic="test")
        
        # Final step should be summarize
        assert result["current_step"] == "summarize"
