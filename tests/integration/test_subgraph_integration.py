"""Integration tests for subgraph functionality.

Tests end-to-end subgraph execution with mocked LLM calls.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def subgraph_graphs(tmp_path: Path) -> tuple[Path, Path]:
    """Create parent and child graph files for testing."""
    # Create prompts directory
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Create child prompt
    child_prompt = prompts_dir / "child" / "process.yaml"
    child_prompt.parent.mkdir()
    child_prompt.write_text(
        """
system: You are a processor.
user: Process this: {input_text}
"""
    )

    # Create parent prompts
    parent_prompt_dir = prompts_dir / "parent"
    parent_prompt_dir.mkdir()
    (parent_prompt_dir / "prepare.yaml").write_text(
        """
system: You are a preparer.
user: Prepare this: {raw_text}
"""
    )
    (parent_prompt_dir / "finalize.yaml").write_text(
        """
system: You are a finalizer.
user: Finalize this: {processed}
"""
    )

    # Create child subgraph
    subgraphs_dir = tmp_path / "graphs" / "subgraphs"
    subgraphs_dir.mkdir(parents=True)
    child_graph = subgraphs_dir / "processor.yaml"
    child_graph.write_text(
        """
version: "1.0"
name: processor
state:
  input_text: str
  output_text: str
nodes:
  process:
    type: llm
    prompt: child/process
    state_key: output_text
edges:
  - {from: START, to: process}
  - {from: process, to: END}
"""
    )

    # Create parent graph
    parent_graph = tmp_path / "graphs" / "parent.yaml"
    parent_graph.write_text(
        """
version: "1.0"
name: parent
state:
  raw_text: str
  prepared: str
  processed: str
  final: str
nodes:
  prepare:
    type: llm
    prompt: parent/prepare
    state_key: prepared
  process:
    type: subgraph
    mode: invoke
    graph: subgraphs/processor.yaml
    input_mapping:
      prepared: input_text
    output_mapping:
      processed: output_text
  finalize:
    type: llm
    prompt: parent/finalize
    state_key: final
edges:
  - {from: START, to: prepare}
  - {from: prepare, to: process}
  - {from: process, to: finalize}
  - {from: finalize, to: END}
"""
    )

    return parent_graph, child_graph


class TestSubgraphIntegration:
    """End-to-end subgraph tests with mocked LLM."""

    @pytest.mark.req("REQ-YG-042")
    def test_runs_parent_to_subgraph_to_parent(self, subgraph_graphs, monkeypatch):
        """Runs parent → subgraph → parent flow successfully."""

        from yamlgraph.graph_loader import compile_graph, load_graph_config

        parent_graph, _ = subgraph_graphs
        prompts_dir = parent_graph.parent.parent / "prompts"

        # Set prompts directory
        monkeypatch.setenv("YAMLGRAPH_PROMPTS_DIR", str(prompts_dir))

        # Mock execute_prompt to return predictable results
        call_count = {"count": 0}

        def mock_execute(prompt_name, **kwargs):
            call_count["count"] += 1
            if "prepare" in prompt_name:
                return "prepared text"
            elif "process" in prompt_name:
                return "processed text"
            elif "finalize" in prompt_name:
                return "final text"
            return f"mocked response for {prompt_name}"

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", side_effect=mock_execute
        ):
            config = load_graph_config(parent_graph)
            graph = compile_graph(config)
            compiled = graph.compile()

            result = compiled.invoke({"raw_text": "test input"})

        # Verify all nodes ran
        assert result["prepared"] == "prepared text"
        assert result["processed"] == "processed text"
        assert result["final"] == "final text"
        assert call_count["count"] == 3  # prepare + process (subgraph) + finalize

    @pytest.mark.req("REQ-YG-042")
    def test_subgraph_state_mapping_works(self, subgraph_graphs, monkeypatch):
        """Input/output mapping correctly transforms state."""
        from yamlgraph.graph_loader import compile_graph, load_graph_config

        parent_graph, _ = subgraph_graphs
        prompts_dir = parent_graph.parent.parent / "prompts"
        monkeypatch.setenv("YAMLGRAPH_PROMPTS_DIR", str(prompts_dir))

        captured_inputs = {}

        def mock_execute(prompt_name, **kwargs):
            captured_inputs[prompt_name] = kwargs.get("variables", {})
            if "prepare" in prompt_name:
                return "PREPARED"
            elif "process" in prompt_name:
                # This should receive input_text (mapped from prepared)
                return "PROCESSED"
            elif "finalize" in prompt_name:
                return "FINAL"
            return "mock"

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", side_effect=mock_execute
        ):
            config = load_graph_config(parent_graph)
            graph = compile_graph(config)
            compiled = graph.compile()

            result = compiled.invoke({"raw_text": "original"})

        # Check that subgraph received mapped input
        assert "child/process" in captured_inputs
        # The subgraph should have input_text (mapped from parent's prepared)
        assert captured_inputs["child/process"].get("input_text") == "PREPARED"

        # Check output was mapped back
        assert result["processed"] == "PROCESSED"

    @pytest.mark.req("REQ-YG-042")
    def test_nested_subgraphs(self, tmp_path, monkeypatch):
        """Supports subgraph within subgraph (2 levels deep)."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Level 2 (deepest)
        (prompts_dir / "level2").mkdir()
        (prompts_dir / "level2" / "process.yaml").write_text(
            "system: L2\nuser: {data}"  # Use 'data' to avoid skip
        )

        # Level 1
        (prompts_dir / "level1").mkdir()
        (prompts_dir / "level1" / "pre.yaml").write_text(
            "system: L1\nuser: {input}"  # Use 'input' to avoid skip
        )

        graphs_dir = tmp_path / "graphs"
        graphs_dir.mkdir()
        (graphs_dir / "subgraphs").mkdir()

        # Level 2 graph
        (graphs_dir / "subgraphs" / "level2.yaml").write_text(
            """
version: "1.0"
name: level2
state:
  data: str
  output: str
nodes:
  work:
    type: llm
    prompt: level2/process
    state_key: output
edges:
  - {from: START, to: work}
  - {from: work, to: END}
"""
        )

        # Level 1 graph (calls level 2)
        (graphs_dir / "subgraphs" / "level1.yaml").write_text(
            """
version: "1.0"
name: level1
state:
  input: str
  prepared: str
  output: str
nodes:
  pre:
    type: llm
    prompt: level1/pre
    state_key: prepared
  nested:
    type: subgraph
    mode: invoke
    graph: level2.yaml
    input_mapping:
      prepared: data
    output_mapping:
      output: output
edges:
  - {from: START, to: pre}
  - {from: pre, to: nested}
  - {from: nested, to: END}
"""
        )

        # Root graph (calls level 1)
        root = graphs_dir / "root.yaml"
        root.write_text(
            """
version: "1.0"
name: root
state:
  start: str
  result: str
nodes:
  delegate:
    type: subgraph
    mode: invoke
    graph: subgraphs/level1.yaml
    input_mapping:
      start: input
    output_mapping:
      result: output
edges:
  - {from: START, to: delegate}
  - {from: delegate, to: END}
"""
        )

        monkeypatch.setenv("YAMLGRAPH_PROMPTS_DIR", str(prompts_dir))

        call_sequence = []

        def mock_execute(prompt_name, **kwargs):
            call_sequence.append(prompt_name)
            return f"result from {prompt_name}"

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", side_effect=mock_execute
        ):
            from yamlgraph.graph_loader import compile_graph, load_graph_config

            config = load_graph_config(root)
            graph = compile_graph(config)
            compiled = graph.compile()

            result = compiled.invoke({"start": "hello"})

        # Both levels should have executed
        assert "level1/pre" in call_sequence
        assert "level2/process" in call_sequence
        assert result["result"] == "result from level2/process"
