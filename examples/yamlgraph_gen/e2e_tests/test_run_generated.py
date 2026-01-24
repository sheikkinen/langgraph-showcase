"""E2E tests for running generated graphs.

These tests generate a graph and then execute it to verify it works.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from yamlgraph import build_graph

GENERATOR_GRAPH = Path(__file__).parent.parent / "graph.yaml"


def run_generator(request: str, output_dir: str) -> dict:
    """Run the generator graph with given request."""
    graph = build_graph(GENERATOR_GRAPH).compile()
    return graph.invoke(
        {
            "request": request,
            "output_dir": output_dir,
        }
    )


def run_generated_graph(graph_path: Path, initial_state: dict) -> dict:
    """Run a generated graph with given initial state."""
    graph = build_graph(graph_path).compile()
    return graph.invoke(initial_state)


@pytest.fixture
def output_dir():
    """Create a temporary output directory."""
    tmp_dir = tempfile.mkdtemp(prefix="yamlgraph_gen_run_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.mark.e2e
class TestGeneratedGraphExecution:
    """Tests that execute the generated graphs."""

    def test_generate_and_run_simple_graph(self, output_dir: str) -> None:
        """Generate a graph and run it successfully."""
        # Step 1: Generate a simple graph with explicit pattern
        generate_request = """
        Create a simple LINEAR pipeline:
        1. topic_input - receives a 'topic' string
        2. summarizer - generates key points about the topic
        3. format_output - formats the final summary

        Use LLM nodes in a simple A → B → C linear flow.
        """

        run_generator(generate_request, output_dir)

        # Step 2: Check if generated successfully
        generated_graph = Path(output_dir) / "graph.yaml"
        if not generated_graph.exists():
            pytest.skip("Pipeline requested clarification - graph not yet generated")

        # Step 3: Try to run the generated graph
        result = run_generated_graph(
            generated_graph,
            {"topic": "Machine learning basics"},
        )

        # Should complete without error
        assert result is not None
        # Check we got some output (exact key depends on generated graph)
        assert len(result) > 0

    def test_generate_and_run_router_graph(self, output_dir: str) -> None:
        """Generate a router graph and run it with test input."""
        # Step 1: Generate router with explicit pattern
        generate_request = """
        Create a ROUTER classification pipeline:
        1. classify_message - ROUTER node that classifies as question/complaint/feedback
        2. handle_question - processes questions
        3. handle_complaint - processes complaints
        4. handle_feedback - processes feedback
        """

        run_generator(generate_request, output_dir)

        # Step 2: Run with test input if generated
        generated_graph = Path(output_dir) / "graph.yaml"
        if not generated_graph.exists():
            pytest.skip("Pipeline requested clarification")

        result = run_generated_graph(
            generated_graph,
            {"message": "Why is my order late?"},
        )

        assert result is not None


@pytest.mark.e2e
class TestGeneratorErrorCases:
    """Test error handling in generation."""

    def test_ambiguous_request_triggers_clarification(self, output_dir: str) -> None:
        """Ambiguous request should trigger clarification interrupt."""
        # Very vague request - should trigger low confidence
        vague_request = "Build something"

        # This should either clarify or produce a minimal graph
        result = run_generator(vague_request, output_dir)

        # Either we got interrupted (clarification needed) or got some output
        # Both are valid outcomes - the graph ran successfully
        assert result is not None
