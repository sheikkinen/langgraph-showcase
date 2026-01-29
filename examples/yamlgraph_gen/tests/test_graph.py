"""Graph validation tests for yamlgraph-generator."""

from pathlib import Path

import pytest
import yaml

EXAMPLE_DIR = Path(__file__).parent.parent


class TestGraphValidation:
    """Tests that validate the generator graph structure."""

    def test_graph_yaml_is_valid_yaml(self) -> None:
        """Graph file is valid YAML."""
        graph_path = EXAMPLE_DIR / "graph.yaml"
        content = graph_path.read_text()

        parsed = yaml.safe_load(content)

        assert parsed["version"] == "1.0"
        assert parsed["name"] == "yamlgraph-generator"

    def test_graph_has_required_sections(self) -> None:
        """Graph has all required sections."""
        graph_path = EXAMPLE_DIR / "graph.yaml"
        parsed = yaml.safe_load(graph_path.read_text())

        assert "nodes" in parsed
        assert "edges" in parsed
        assert "state" in parsed

    def test_graph_nodes_have_prompts(self) -> None:
        """All LLM/router nodes reference existing prompts."""
        graph_path = EXAMPLE_DIR / "graph.yaml"
        parsed = yaml.safe_load(graph_path.read_text())

        for node_name, node_config in parsed["nodes"].items():
            node_type = node_config.get("type", "llm")
            if node_type in ("llm", "router", "interrupt"):
                prompt_ref = node_config.get("prompt")
                assert prompt_ref, f"Node {node_name} missing prompt"

                # Check prompt file exists (add prompts/ prefix and .yaml suffix)
                full_path = EXAMPLE_DIR / "prompts" / f"{prompt_ref}.yaml"
                assert full_path.exists(), f"Prompt not found: {full_path}"

    def test_all_prompts_have_required_keys(self) -> None:
        """All prompt files have system and user keys."""
        prompts_dir = EXAMPLE_DIR / "prompts"

        for prompt_file in prompts_dir.glob("*.yaml"):
            content = yaml.safe_load(prompt_file.read_text())
            assert "system" in content, f"{prompt_file.name} missing system"
            assert "user" in content, f"{prompt_file.name} missing user"

    def test_graph_edges_reference_valid_nodes(self) -> None:
        """All edges reference nodes that exist."""
        graph_path = EXAMPLE_DIR / "graph.yaml"
        parsed = yaml.safe_load(graph_path.read_text())

        node_names = set(parsed["nodes"].keys()) | {"START", "END"}

        for edge in parsed["edges"]:
            from_node = edge["from"]
            assert from_node in node_names, f"Unknown from node: {from_node}"

            # Handle conditional edges
            if "to" in edge:
                to_node = edge["to"]
                # to can be a single node name or a list for conditional edges
                if isinstance(to_node, list):
                    for node in to_node:
                        assert node in node_names, f"Unknown to node: {node}"
                else:
                    assert to_node in node_names, f"Unknown to node: {to_node}"
            elif "conditions" in edge:
                for condition in edge["conditions"]:
                    to_node = condition["to"]
                    assert to_node in node_names, f"Unknown to node: {to_node}"

    def test_snippets_are_valid_yaml(self) -> None:
        """All snippet files are valid YAML."""
        snippets_dir = EXAMPLE_DIR / "snippets"

        for snippet_file in snippets_dir.rglob("*.yaml"):
            content = snippet_file.read_text()
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {snippet_file}: {e}")

    def test_pattern_snippets_have_nodes_and_edges(self) -> None:
        """Pattern snippets include both nodes and edges."""
        patterns_dir = EXAMPLE_DIR / "snippets" / "patterns"

        for pattern_file in patterns_dir.glob("*.yaml"):
            content = yaml.safe_load(pattern_file.read_text())
            assert "nodes" in content, f"{pattern_file.name} missing nodes"
            assert "edges" in content, f"{pattern_file.name} missing edges"


class TestGraphLinter:
    """Tests using the yamlgraph linter."""

    def test_graph_passes_lint(self) -> None:
        """Graph passes yamlgraph lint checks."""
        from yamlgraph.linter import lint_graph

        graph_path = EXAMPLE_DIR / "graph.yaml"

        # Use the internal linter function
        result = lint_graph(str(graph_path))

        # Should have no critical errors (warnings are ok)
        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) == 0, f"Lint errors: {errors}"
