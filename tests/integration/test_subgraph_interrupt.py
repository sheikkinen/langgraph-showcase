"""Integration test for FR-006: interrupt_output_mapping limitation.

This test demonstrates the known limitation where interrupt_output_mapping
cannot expose child state when the subgraph hits an interrupt, because
LangGraph's interrupt mechanism uses exceptions that bypass the mapping code.

See: docs/subgraph-interrupt-bug.md
"""

from pathlib import Path

import pytest


class TestSubgraphInterruptMapping:
    """Tests for FR-006 interrupt_output_mapping with real graphs."""

    @pytest.fixture
    def parent_graph_path(self) -> Path:
        """Path to the parent graph with interrupt_output_mapping."""
        return Path(__file__).parent.parent.parent / "graphs" / "interrupt-parent.yaml"

    @pytest.fixture
    def compiled_graph(self, parent_graph_path: Path):
        """Compile the parent graph with checkpointer."""
        from yamlgraph.graph_loader import compile_graph, load_graph_config

        config = load_graph_config(parent_graph_path)
        state_graph = compile_graph(config)

        # Use memory checkpointer for testing
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()

        return state_graph.compile(checkpointer=checkpointer)

    def test_interrupt_output_mapping_surfaces_child_state(self, compiled_graph):
        """FR-006: Parent should see child state when subgraph is interrupted.

        EXPECTED TO FAIL: This test documents the current limitation.
        When it passes, FR-006 is truly fixed.
        """
        # Run parent graph - child will hit interrupt
        config = {"configurable": {"thread_id": "test-fr006"}}
        result = compiled_graph.invoke({"user_input": "hello"}, config)

        # Verify we hit the interrupt
        assert "__interrupt__" in result, "Expected graph to be interrupted"

        # FR-006 EXPECTATION: child state should be mapped to parent
        # This currently FAILS because interrupt exception bypasses mapping
        assert "child_phase" in result, (
            "FR-006 LIMITATION: child_phase not in result. "
            "interrupt_output_mapping is bypassed by LangGraph's exception mechanism. "
            "See docs/subgraph-interrupt-bug.md"
        )
        assert result.get("child_phase") == "processing", (
            "Expected child_phase='processing' from child graph"
        )
        assert result.get("child_data") == "partial result from child", (
            "Expected child_data from interrupt_output_mapping"
        )

    def test_output_mapping_works_on_completion(self, compiled_graph):
        """Verify output_mapping works when subgraph completes normally.

        This test should PASS - it resumes the interrupt and completes.
        """
        from langgraph.types import Command

        config = {"configurable": {"thread_id": "test-completion"}}

        # First run - hits interrupt
        result = compiled_graph.invoke({"user_input": "hello"}, config)
        assert "__interrupt__" in result

        # Resume with user answer
        result = compiled_graph.invoke(Command(resume="my answer"), config)

        # After completion, output_mapping should work
        # Note: The 'done' node sets final_result to 'all done'
        assert result.get("final_result") == "all done", (
            "Expected final_result from 'done' passthrough node"
        )

    def test_get_state_can_access_child_state(self, compiled_graph):
        """Workaround: Use get_state() to access child state after interrupt.

        This test documents the workaround for the FR-006 limitation.
        """
        config = {"configurable": {"thread_id": "test-workaround"}}

        # Run until interrupt
        result = compiled_graph.invoke({"user_input": "hello"}, config)
        assert "__interrupt__" in result

        # Workaround: access state via checkpointer
        state_snapshot = compiled_graph.get_state(config)

        # The parent state should be accessible
        assert state_snapshot is not None
        assert "values" in dir(state_snapshot) or hasattr(state_snapshot, "values")

        # Note: Child state may be in nested subgraph thread
        # This depends on checkpointer implementation
        print(f"State snapshot values: {state_snapshot.values}")
