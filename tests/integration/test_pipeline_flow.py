"""Integration tests for the complete pipeline flow."""

from yamlgraph.builder import build_graph


class TestBuildGraph:
    """Tests for build_graph function."""

    def test_graph_compiles(self):
        """Graph should compile without errors."""
        graph = build_graph()
        compiled = graph.compile()
        assert compiled is not None

    def test_graph_has_expected_nodes(self):
        """Graph should have generate, analyze, summarize nodes."""
        graph = build_graph()
        # StateGraph stores nodes internally
        assert "generate" in graph.nodes
        assert "analyze" in graph.nodes
        assert "summarize" in graph.nodes
