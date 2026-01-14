"""Tests for issues that were identified and fixed.

These tests verify the fixes for issues documented in docs/open-issues.md.
"""

import pytest
from unittest.mock import patch

from showcase.builder import build_resume_graph
from showcase.graph_loader import (
    load_graph_config,
    _should_continue,
)
from showcase.models import Analysis, GeneratedContent, create_initial_state


# =============================================================================
# Issue 1: Resume Logic - FIXED: skip_if_exists behavior
# =============================================================================


class TestResumeStartFromParameter:
    """Issue 1: Resume should skip nodes whose output already exists."""

    @patch("showcase.node_factory.execute_prompt")
    def test_resume_from_analyze_skips_generate(self, mock_execute):
        """When state has 'generated', generate node should be skipped.
        
        Resume works via skip_if_exists: if output already in state, skip LLM call.
        """
        # State with generated content already present
        state = create_initial_state(topic="test", thread_id="issue1")
        state["generated"] = GeneratedContent(
            title="Already Generated",
            content="This was generated in a previous run",
            word_count=10,
            tags=[],
        )
        
        # Only mock analyze and summarize - generate should be skipped
        mock_analysis = Analysis(
            summary="Analysis",
            key_points=["Point"],
            sentiment="neutral",
            confidence=0.8,
        )
        mock_execute.side_effect = [mock_analysis, "Final summary"]
        
        graph = build_resume_graph().compile()
        result = graph.invoke(state)
        
        # Expected: 2 calls (analyze, summarize) - generate skipped
        assert mock_execute.call_count == 2, (
            f"Expected 2 LLM calls (analyze, summarize), "
            f"but got {mock_execute.call_count}. "
            f"Generate should be skipped when 'generated' exists!"
        )
        # Original generated content should be preserved
        assert result["generated"].title == "Already Generated"

    @patch("showcase.node_factory.execute_prompt")
    def test_resume_from_summarize_skips_generate_and_analyze(self, mock_execute):
        """When state has 'generated' and 'analysis', only summarize runs.
        """
        state = create_initial_state(topic="test", thread_id="issue1b")
        state["generated"] = GeneratedContent(
            title="Done",
            content="Content",
            word_count=5,
            tags=[],
        )
        state["analysis"] = Analysis(
            summary="Done",
            key_points=["Point"],
            sentiment="positive",
            confidence=0.9,
        )
        
        mock_execute.return_value = "Final summary"
        
        graph = build_resume_graph().compile()
        result = graph.invoke(state)
        
        # Expected: 1 call (summarize only)
        assert mock_execute.call_count == 1, (
            f"Expected 1 LLM call (summarize only), "
            f"but got {mock_execute.call_count}. "
            f"Generate and analyze should be skipped!"
        )
        # Original content should be preserved
        assert result["generated"].title == "Done"
        assert result["analysis"].summary == "Done"

    def test_resume_preserves_existing_generated_content(self):
        """Resuming should NOT overwrite already-generated content."""
        # Covered by test_resume_from_analyze_skips_generate
        pass


# =============================================================================
# Issue 2: Conditions Block is Dead Config
# =============================================================================


class TestConditionsFromYAML:
    """Issue 2: Conditions block was dead config - now removed."""

    def test_routing_uses_should_continue_function(self):
        """Routing is handled by _should_continue(), not YAML conditions.
        
        This is by design: dynamic condition evaluation adds complexity
        without clear benefit for this showcase. The _should_continue()
        function provides simple, predictable routing.
        """
        # _should_continue checks 'generated' and 'error'
        state_success = {
            "generated": GeneratedContent(
                title="T", content="C", word_count=5, tags=[]
            ),
            "error": None,
        }
        state_error = {"generated": None, "error": "Some error"}
        
        assert _should_continue(state_success) == "continue"
        assert _should_continue(state_error) == "end"

    def test_conditions_block_not_in_schema(self):
        """GraphConfig no longer parses conditions block."""
        from showcase.config import DEFAULT_GRAPH
        
        config = load_graph_config(DEFAULT_GRAPH)
        
        # conditions attribute should not exist
        assert not hasattr(config, "conditions"), (
            "GraphConfig should not have 'conditions' attribute - it's dead config"
        )


# =============================================================================
# Issue 5: _entry_point hack
# =============================================================================


class TestEntryPointHack:
    """Issue 5: Using private _entry_point is fragile."""

    @pytest.fixture
    def simple_yaml(self, tmp_path):
        """Minimal YAML for testing."""
        yaml_content = """
version: "1.0"
name: test
state_class: showcase.models.ShowcaseState
nodes:
  first:
    type: llm
    prompt: generate
    output_model: showcase.models.GeneratedContent
    state_key: generated
edges:
  - from: START
    to: first
  - from: first
    to: END
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)
        return yaml_file

    def test_entry_point_accessible_via_behavior(self, simple_yaml):
        """Entry point should be testable via graph behavior, not private attrs.
        
        Currently graph_loader.py sets graph._entry_point for testing.
        This test shows how to test entry point via behavior instead.
        """
        from showcase.graph_loader import load_and_compile
        
        graph = load_and_compile(simple_yaml)
        _ = graph.compile()  # Verify it compiles
        
        # Get the graph structure - this is the proper way
        # The first node after START should be 'first'
        nodes = list(graph.nodes.keys())
        assert "first" in nodes
        
        # We can also check by looking at edges from __start__
        # But testing via invocation is more robust
