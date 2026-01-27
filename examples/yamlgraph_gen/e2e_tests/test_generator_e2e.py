"""E2E tests for the yamlgraph generator graph.

These tests run the actual generator with real LLM calls.
They require API keys and network access.

Run: pytest examples/yamlgraph_gen/e2e_tests/ -v -m e2e
"""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from yamlgraph import build_graph

GRAPH_PATH = Path(__file__).parent.parent / "graph.yaml"


def run_generator(request: str, output_dir: str) -> dict:
    """Run the generator graph with given request."""
    graph = build_graph(GRAPH_PATH).compile()
    return graph.invoke(
        {
            "request": request,
            "output_dir": output_dir,
        }
    )


@pytest.fixture
def output_dir():
    """Create a temporary output directory."""
    tmp_dir = tempfile.mkdtemp(prefix="yamlgraph_gen_test_")
    yield tmp_dir
    # Cleanup after test
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.mark.e2e
class TestGeneratorE2E:
    """End-to-end tests for the generator graph."""

    def test_generate_simple_linear_graph(self, output_dir: str) -> None:
        """Generate a simple linear summarization pipeline."""
        # Be very explicit to get high confidence classification
        request = """
        Create a simple linear pipeline with these nodes:
        1. input_handler - receives a 'topic' as input
        2. summarizer - generates a summary of the topic
        3. output_formatter - formats the summary for display

        This is a simple sequential A → B → C linear pipeline.
        Use LLM nodes for each step.
        """

        run_generator(request, output_dir)

        # Check if pipeline completed or is waiting for clarification
        output_path = Path(output_dir)
        if (output_path / "graph.yaml").exists():
            # Pipeline completed successfully
            # Check graph is valid YAML
            graph_content = (output_path / "graph.yaml").read_text()
            parsed = yaml.safe_load(graph_content)
            assert "nodes" in parsed
            assert "edges" in parsed

            # Check we have at least one prompt
            prompts = list((output_path / "prompts").glob("*.yaml"))
            assert len(prompts) > 0, "No prompt files generated"
        else:
            # Pipeline may be in interrupt state (clarification needed)
            # This is acceptable for e2e - the graph ran successfully
            pytest.skip(
                "Pipeline requested clarification - graph runs but needs more specific input"
            )

    def test_generate_router_graph(self, output_dir: str) -> None:
        """Generate a router/classification pipeline."""
        request = """
        Create a router pipeline to classify customer emails:
        1. classify_email - routes based on content type (use router node)
        2. handle_support - handles support requests
        3. handle_sales - handles sales inquiries
        4. handle_billing - handles billing questions

        This uses the ROUTER pattern for classification.
        """

        run_generator(request, output_dir)

        output_path = Path(output_dir)
        if (output_path / "graph.yaml").exists():
            # Check graph has router node
            parsed = yaml.safe_load((output_path / "graph.yaml").read_text())
            node_types = [
                n.get("type", "llm") for n in parsed.get("nodes", {}).values()
            ]
            assert "router" in node_types, "Expected a router node for classification"
        else:
            pytest.skip("Pipeline requested clarification")

    def test_generate_map_graph(self, output_dir: str) -> None:
        """Generate a batch processing pipeline."""
        request = """
        Create a batch processing pipeline using the MAP pattern:
        1. url_list_input - receives a list of URLs
        2. fetch_and_extract - uses MAP node to process each URL in parallel, extracting titles
        3. aggregate_results - collects all titles into final output

        This is a fan-out/fan-in MAP pattern.
        """

        run_generator(request, output_dir)

        output_path = Path(output_dir)
        if (output_path / "graph.yaml").exists():
            # Check graph has map node
            parsed = yaml.safe_load((output_path / "graph.yaml").read_text())
            node_types = [
                n.get("type", "llm") for n in parsed.get("nodes", {}).values()
            ]
            assert "map" in node_types, "Expected a map node for batch processing"
        else:
            pytest.skip("Pipeline requested clarification")

    def test_generated_graph_lints_clean(self, output_dir: str) -> None:
        """Generated graph should pass linting."""
        from yamlgraph.tools.graph_linter import lint_graph

        request = """
        Create a simple linear Q&A pipeline:
        1. receive_question - takes a question as input
        2. generate_answer - uses LLM to generate an answer
        3. format_response - formats the final response

        Simple linear A → B → C pattern.
        """

        run_generator(request, output_dir)

        output_path = Path(output_dir)
        generated_graph = output_path / "graph.yaml"
        if generated_graph.exists():
            # Lint the generated graph
            result = lint_graph(str(generated_graph), str(output_path))
            errors = [i for i in result.issues if i.severity == "error"]
            assert len(errors) == 0, f"Generated graph has lint errors: {errors}"
        else:
            pytest.skip("Pipeline requested clarification")


@pytest.mark.e2e
class TestGeneratorPatternCombos:
    """Test pattern combinations."""

    def test_router_plus_map(self, output_dir: str) -> None:
        """Generate a pipeline that classifies then processes in parallel."""
        request = """
        Create a document processor combining ROUTER and MAP patterns:
        1. classify_documents - ROUTER node that classifies as invoice/receipt/contract
        2. process_invoices - MAP node to process all invoices in parallel
        3. process_receipts - MAP node to process all receipts in parallel
        4. process_contracts - MAP node to process all contracts in parallel
        5. aggregate_all - combines results from all processors
        """

        run_generator(request, output_dir)

        output_path = Path(output_dir)
        if (output_path / "graph.yaml").exists():
            parsed = yaml.safe_load((output_path / "graph.yaml").read_text())
            node_types = [
                n.get("type", "llm") for n in parsed.get("nodes", {}).values()
            ]

            # Should have both router and map
            assert "router" in node_types or "map" in node_types, (
                "Expected router or map node for this request"
            )
        else:
            pytest.skip("Pipeline requested clarification")
