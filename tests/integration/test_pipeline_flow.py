"""Integration tests for the complete pipeline flow."""

import pytest

from yamlgraph.graph_loader import load_and_compile


class TestLoadAndCompile:
    """Tests for load_and_compile function."""

    @pytest.mark.req("REQ-YG-005", "REQ-YG-014")
    def test_graph_compiles(self):
        """Graph should compile without errors."""
        graph = load_and_compile("examples/demos/yamlgraph/graph.yaml")
        compiled = graph.compile()
        assert compiled is not None

    @pytest.mark.req("REQ-YG-005", "REQ-YG-014")
    def test_graph_has_expected_nodes(self):
        """Graph should have generate, analyze, summarize nodes."""
        graph = load_and_compile("examples/demos/yamlgraph/graph.yaml")
        # StateGraph stores nodes internally
        assert "generate" in graph.nodes
        assert "analyze" in graph.nodes
        assert "summarize" in graph.nodes
