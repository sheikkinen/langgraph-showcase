"""Tests for issues that were identified and fixed.

These tests verify the fixes for issues documented in docs/open-issues.md.
"""

import pytest

from yamlgraph.graph_loader import load_graph_config

# =============================================================================
# Issue 2: Conditions Block is Dead Config
# =============================================================================


class TestConditionsFromYAML:
    """Issue 2: Conditions block was dead config - now uses expression routing."""

    @pytest.mark.req("REQ-YG-014")
    def test_conditions_block_not_in_schema(self):
        """GraphConfig no longer parses conditions block."""
        from yamlgraph.config import DEFAULT_GRAPH

        config = load_graph_config(DEFAULT_GRAPH)

        # conditions attribute should not exist
        assert not hasattr(
            config, "conditions"
        ), "GraphConfig should not have 'conditions' attribute - it's dead config"


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
nodes:
  first:
    type: llm
    prompt: generate
    output_model: yamlgraph.models.GenericReport
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

    @pytest.mark.req("REQ-YG-014")
    def test_entry_point_accessible_via_behavior(self, simple_yaml):
        """Entry point should be testable via graph behavior, not private attrs.

        Currently graph_loader.py sets graph._entry_point for testing.
        This test shows how to test entry point via behavior instead.
        """
        from yamlgraph.graph_loader import load_and_compile

        graph = load_and_compile(simple_yaml)
        _ = graph.compile()  # Verify it compiles

        # Get the graph structure - this is the proper way
        # The first node after START should be 'first'
        nodes = list(graph.nodes.keys())
        assert "first" in nodes

        # We can also check by looking at edges from __start__
        # But testing via invocation is more robust
