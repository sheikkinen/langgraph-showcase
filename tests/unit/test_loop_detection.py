"""Tests for loop detection in graph_loader.

These tests validate the bug where detect_loop_nodes marks ALL ancestors
as loop nodes, not just the nodes in the actual cycle.
"""

import pytest

from yamlgraph.graph_loader import detect_loop_nodes


class TestDetectLoopNodes:
    """Tests for detect_loop_nodes function."""

    @pytest.mark.req("REQ-YG-006")
    def test_simple_cycle_only_marks_cycle_nodes(self) -> None:
        """Test that only cycle nodes are marked, not ancestors.

        Graph: START → A → B → C → B (loop back)

        Expected: Only B and C are in the loop
        Bug behavior: A, B, and C are all marked as loop nodes
        """
        edges = [
            {"from": "START", "to": "A"},
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "B"},  # Back edge creates B-C cycle
            {"from": "C", "to": "END"},
        ]

        loop_nodes = detect_loop_nodes(edges)

        # Only B and C should be in the loop
        assert "B" in loop_nodes, "B should be detected as loop node"
        assert "C" in loop_nodes, "C should be detected as loop node"

        # A is NOT part of the cycle - it's an ancestor
        assert (
            "A" not in loop_nodes
        ), "A should NOT be marked as loop node (it's an ancestor, not in cycle)"
        assert "START" not in loop_nodes, "START should NOT be marked as loop node"
        assert "END" not in loop_nodes, "END should NOT be marked as loop node"

    @pytest.mark.req("REQ-YG-006")
    def test_self_loop_only_marks_self(self) -> None:
        """Test that a self-loop only marks the looping node.

        Graph: START → A → B → B (self-loop)
        """
        edges = [
            {"from": "START", "to": "A"},
            {"from": "A", "to": "B"},
            {"from": "B", "to": "B"},  # Self-loop
            {"from": "B", "to": "END"},
        ]

        loop_nodes = detect_loop_nodes(edges)

        assert loop_nodes == {"B"}, f"Only B should be in loop, got: {loop_nodes}"

    @pytest.mark.req("REQ-YG-006")
    def test_longer_chain_with_deep_cycle(self) -> None:
        """Test a longer chain with a cycle deep in the graph.

        Graph: START → A → B → C → D → E → D (cycle D-E)

        Expected: Only D and E are in the loop
        """
        edges = [
            {"from": "START", "to": "A"},
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "C", "to": "D"},
            {"from": "D", "to": "E"},
            {"from": "E", "to": "D"},  # Back edge creates D-E cycle
            {"from": "E", "to": "END"},
        ]

        loop_nodes = detect_loop_nodes(edges)

        assert "D" in loop_nodes
        assert "E" in loop_nodes
        # A, B, C should NOT be marked
        assert "A" not in loop_nodes, "A is not in the cycle"
        assert "B" not in loop_nodes, "B is not in the cycle"
        assert "C" not in loop_nodes, "C is not in the cycle"

    @pytest.mark.req("REQ-YG-006")
    def test_multiple_cycles_correctly_identified(self) -> None:
        """Test graph with multiple independent cycles.

        Graph: START → A → B → A (cycle 1)
                       ↓
                       C → D → C (cycle 2)
        """
        edges = [
            {"from": "START", "to": "A"},
            {"from": "A", "to": "B"},
            {"from": "B", "to": "A"},  # Cycle 1: A-B
            {"from": "A", "to": "C"},
            {"from": "C", "to": "D"},
            {"from": "D", "to": "C"},  # Cycle 2: C-D
            {"from": "D", "to": "END"},
        ]

        loop_nodes = detect_loop_nodes(edges)

        # Both cycles should be detected
        assert "A" in loop_nodes
        assert "B" in loop_nodes
        assert "C" in loop_nodes
        assert "D" in loop_nodes
        # START and END are not in any cycle
        assert "START" not in loop_nodes
        assert "END" not in loop_nodes

    @pytest.mark.req("REQ-YG-006")
    def test_no_cycle_returns_empty(self) -> None:
        """Test linear graph returns no loop nodes."""
        edges = [
            {"from": "START", "to": "A"},
            {"from": "A", "to": "B"},
            {"from": "B", "to": "END"},
        ]

        loop_nodes = detect_loop_nodes(edges)
        assert loop_nodes == set()

    @pytest.mark.req("REQ-YG-006")
    def test_reflexion_pattern(self) -> None:
        """Test real-world reflexion pattern (critique → refine → critique).

        Graph: START → draft → critique → refine → critique (loop)
                                     ↓
                                    END

        Only critique and refine are in the loop.
        draft is NOT - it runs once before entering the loop.
        """
        edges = [
            {"from": "START", "to": "draft"},
            {"from": "draft", "to": "critique"},
            {"from": "critique", "to": "refine"},
            {"from": "critique", "to": "END"},  # Conditional exit
            {"from": "refine", "to": "critique"},  # Loop back
        ]

        loop_nodes = detect_loop_nodes(edges)

        assert "critique" in loop_nodes, "critique is in the loop"
        assert "refine" in loop_nodes, "refine is in the loop"
        # draft runs ONCE before entering the loop - it's not part of the cycle
        assert (
            "draft" not in loop_nodes
        ), "draft should NOT be in the loop (runs once before cycle)"
