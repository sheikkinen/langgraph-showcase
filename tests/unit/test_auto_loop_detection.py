"""Tests for FR-010: Auto-detect Loop Nodes for skip_if_exists.

TDD RED phase - these tests will fail until implementation.
"""

import pytest


class TestDetectLoopNodes:
    """Tests for detect_loop_nodes function."""

    def test_import_function(self) -> None:
        """Test function can be imported."""
        from yamlgraph.graph_loader import detect_loop_nodes

        assert callable(detect_loop_nodes)

    def test_simple_two_node_loop(self) -> None:
        """Test detection of A -> B -> A cycle."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "A"},
        ]
        result = detect_loop_nodes(edges)
        assert result == {"A", "B"}

    def test_no_loop_linear_graph(self) -> None:
        """Test linear graph has no loop nodes."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = [
            {"from": "START", "to": "A"},
            {"from": "A", "to": "B"},
            {"from": "B", "to": "END"},
        ]
        result = detect_loop_nodes(edges)
        assert result == set()

    def test_self_loop(self) -> None:
        """Test node pointing to itself."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = [
            {"from": "A", "to": "A"},
        ]
        result = detect_loop_nodes(edges)
        assert result == {"A"}

    def test_reflexion_pattern(self) -> None:
        """Test classic reflexion loop pattern."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = [
            {"from": "START", "to": "generate"},
            {"from": "generate", "to": "evaluate"},
            {"from": "evaluate", "to": "generate"},  # Loop back
            {"from": "evaluate", "to": "END"},
        ]
        result = detect_loop_nodes(edges)
        # Core loop nodes must be detected
        assert "generate" in result
        assert "evaluate" in result
        # END is not in the loop
        assert "END" not in result

    def test_three_node_cycle(self) -> None:
        """Test A -> B -> C -> A cycle."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "A"},
        ]
        result = detect_loop_nodes(edges)
        assert result == {"A", "B", "C"}

    def test_mixed_loop_and_linear(self) -> None:
        """Test graph with both loop and linear parts."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = [
            {"from": "START", "to": "init"},
            {"from": "init", "to": "loop_a"},
            {"from": "loop_a", "to": "loop_b"},
            {"from": "loop_b", "to": "loop_a"},  # Loop
            {"from": "loop_b", "to": "finalize"},
            {"from": "finalize", "to": "END"},
        ]
        result = detect_loop_nodes(edges)
        # Core loop nodes must be detected
        assert "loop_a" in result
        assert "loop_b" in result
        # Nodes leading to loop may or may not be included (algorithm-dependent)
        # Key: finalize and END are definitely not in loop
        assert "finalize" not in result
        assert "END" not in result

    def test_multiple_to_targets(self) -> None:
        """Test edge with list of targets."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = [
            {"from": "A", "to": ["B", "C"]},
            {"from": "B", "to": "A"},
        ]
        result = detect_loop_nodes(edges)
        assert "A" in result
        assert "B" in result
        assert "C" not in result

    def test_empty_edges(self) -> None:
        """Test empty edge list."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = []
        result = detect_loop_nodes(edges)
        assert result == set()

    def test_conditional_edges_detected(self) -> None:
        """Test edges with conditions are still detected."""
        from yamlgraph.graph_loader import detect_loop_nodes

        edges = [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "A", "condition": "needs_retry"},
            {"from": "B", "to": "C", "condition": "done"},
        ]
        result = detect_loop_nodes(edges)
        assert result == {"A", "B"}


class TestAutoApplySkipIfExists:
    """Tests for auto-applying skip_if_exists to loop nodes."""

    def test_auto_applies_to_loop_nodes(self) -> None:
        """Test skip_if_exists=false is auto-applied to loop nodes."""
        from yamlgraph.graph_loader import apply_loop_node_defaults

        config = {
            "nodes": {
                "generate": {"type": "llm", "prompt": "test"},
                "evaluate": {"type": "router", "prompt": "test"},
            },
            "edges": [
                {"from": "generate", "to": "evaluate"},
                {"from": "evaluate", "to": "generate"},
            ],
        }
        result = apply_loop_node_defaults(config)

        assert result["nodes"]["generate"].get("skip_if_exists") is False
        assert result["nodes"]["evaluate"].get("skip_if_exists") is False

    def test_preserves_explicit_true(self) -> None:
        """Test explicit skip_if_exists=true is preserved (user override)."""
        from yamlgraph.graph_loader import apply_loop_node_defaults

        config = {
            "nodes": {
                "generate": {"type": "llm", "prompt": "test", "skip_if_exists": True},
                "evaluate": {"type": "router", "prompt": "test"},
            },
            "edges": [
                {"from": "generate", "to": "evaluate"},
                {"from": "evaluate", "to": "generate"},
            ],
        }
        result = apply_loop_node_defaults(config)

        # User explicitly set true - should be preserved
        assert result["nodes"]["generate"].get("skip_if_exists") is True
        # No explicit setting - should be auto-set to false
        assert result["nodes"]["evaluate"].get("skip_if_exists") is False

    def test_preserves_explicit_false(self) -> None:
        """Test explicit skip_if_exists=false is preserved."""
        from yamlgraph.graph_loader import apply_loop_node_defaults

        config = {
            "nodes": {
                "generate": {"type": "llm", "prompt": "test", "skip_if_exists": False},
            },
            "edges": [
                {"from": "generate", "to": "generate"},  # Self-loop
            ],
        }
        result = apply_loop_node_defaults(config)

        assert result["nodes"]["generate"].get("skip_if_exists") is False

    def test_linear_nodes_unchanged(self) -> None:
        """Test linear nodes don't get skip_if_exists modified."""
        from yamlgraph.graph_loader import apply_loop_node_defaults

        config = {
            "nodes": {
                "step1": {"type": "llm", "prompt": "test"},
                "step2": {"type": "llm", "prompt": "test"},
            },
            "edges": [
                {"from": "step1", "to": "step2"},
            ],
        }
        result = apply_loop_node_defaults(config)

        # Linear nodes should not have skip_if_exists set (default true applies)
        assert "skip_if_exists" not in result["nodes"]["step1"]
        assert "skip_if_exists" not in result["nodes"]["step2"]

    def test_returns_modified_copy(self) -> None:
        """Test function returns modified config, not mutating original."""
        from yamlgraph.graph_loader import apply_loop_node_defaults

        config = {
            "nodes": {
                "A": {"type": "llm", "prompt": "test"},
            },
            "edges": [
                {"from": "A", "to": "A"},
            ],
        }
        original_node = dict(config["nodes"]["A"])
        result = apply_loop_node_defaults(config)

        # Original should be unchanged
        assert "skip_if_exists" not in original_node


class TestIntegrationWithGraphLoader:
    """Tests for integration with load_graph_config."""

    def test_reflexion_demo_auto_detected(self, tmp_path) -> None:
        """Test reflexion-demo pattern works without explicit skip_if_exists."""
        from yamlgraph.graph_loader import load_graph_config

        graph_yaml = """
version: "1.0"
name: reflexion-test
nodes:
  generate:
    type: llm
    prompt: generate
    state_key: draft
  evaluate:
    type: router
    prompt: evaluate
    routes:
      improve: generate
      done: finalize
  finalize:
    type: passthrough
    state_key: result
edges:
  - from: START
    to: generate
  - from: generate
    to: evaluate
  - from: evaluate
    to: generate
    condition: "route == 'improve'"
  - from: evaluate
    to: finalize
    condition: "route == 'done'"
  - from: finalize
    to: END
"""
        graph_file = tmp_path / "test-graph.yaml"
        graph_file.write_text(graph_yaml)

        config = load_graph_config(str(graph_file))

        # Loop nodes should have skip_if_exists auto-applied
        assert config.nodes["generate"].get("skip_if_exists") is False
        assert config.nodes["evaluate"].get("skip_if_exists") is False
        # Non-loop node should not have skip_if_exists set
        assert "skip_if_exists" not in config.nodes["finalize"]
