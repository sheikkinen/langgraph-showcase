"""Integration test for graph-relative prompt resolution (FR-A)."""

from pathlib import Path
from unittest.mock import patch

from yamlgraph.graph_loader import load_and_compile


class TestColocatedPrompts:
    """Test graphs with prompts colocated next to the graph YAML."""

    def test_prompts_relative_true(self, tmp_path: Path):
        """Graph with prompts_relative: true resolves prompts from graph dir."""
        # Create colocated structure:
        # questionnaires/audit/
        #   graph.yaml
        #   prompts/
        #     opening.yaml
        graph_dir = tmp_path / "questionnaires" / "audit"
        prompts_dir = graph_dir / "prompts"
        prompts_dir.mkdir(parents=True)

        # Create graph
        graph_yaml = """
version: "1.0"
name: audit-questionnaire

defaults:
  prompts_relative: true

nodes:
  generate_opening:
    type: llm
    prompt: prompts/opening
    state_key: opening

edges:
  - from: START
    to: generate_opening
  - from: generate_opening
    to: END
"""
        graph_file = graph_dir / "graph.yaml"
        graph_file.write_text(graph_yaml)

        # Create colocated prompt
        prompt_yaml = """
system: |
  You are a helpful audit assistant.

user: |
  Generate an opening statement for the audit questionnaire.
"""
        prompt_file = prompts_dir / "opening.yaml"
        prompt_file.write_text(prompt_yaml)

        # Mock execute_prompt to avoid LLM call
        mock_result = "Welcome to the audit questionnaire."

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", return_value=mock_result
        ) as mock:
            # Load and compile the graph
            graph = load_and_compile(str(graph_file))
            app = graph.compile()

            # Invoke with initial state
            result = app.invoke({})

            # Verify execute_prompt was called with path params
            mock.assert_called_once()
            call_kwargs = mock.call_args[1]
            assert call_kwargs["prompt_name"] == "prompts/opening"
            # BUG FIX: These params must be passed to execute_prompt
            assert call_kwargs.get("prompts_relative") is True, (
                "prompts_relative should be True"
            )
            assert call_kwargs.get("graph_path") is not None, (
                "graph_path should be passed"
            )

        # Verify result
        assert result["opening"] == mock_result

    def test_explicit_prompts_dir(self, tmp_path: Path):
        """Graph with prompts_dir resolves prompts from explicit path."""
        # Create structure:
        # shared/prompts/greet.yaml
        # graphs/hello.yaml
        shared_prompts = tmp_path / "shared" / "prompts"
        shared_prompts.mkdir(parents=True)
        graphs_dir = tmp_path / "graphs"
        graphs_dir.mkdir()

        # Create prompt in shared location
        prompt_yaml = """
system: Be friendly.
user: Say hello to {name}.
"""
        (shared_prompts / "greet.yaml").write_text(prompt_yaml)

        # Create graph pointing to shared prompts
        graph_yaml = f"""
version: "1.0"
name: hello

defaults:
  prompts_dir: {shared_prompts}

nodes:
  greet:
    type: llm
    prompt: greet
    variables:
      name: "{{{{state.name}}}}"
    state_key: greeting

edges:
  - from: START
    to: greet
  - from: greet
    to: END
"""
        graph_file = graphs_dir / "hello.yaml"
        graph_file.write_text(graph_yaml)

        mock_result = "Hello, World!"

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", return_value=mock_result
        ) as mock:
            graph = load_and_compile(str(graph_file))
            app = graph.compile()

            result = app.invoke({"name": "World"})

            mock.assert_called_once()

        assert result["greeting"] == mock_result
