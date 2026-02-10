"""Tests for graph.yaml configuration - TDD: Red phase."""

from pathlib import Path

import pytest
import yaml


class TestGraphConfig:
    """Test graph.yaml structure and correctness."""

    @pytest.fixture
    def graph_path(self):
        """Path to graph.yaml."""
        return Path(__file__).parent.parent / "graph.yaml"

    @pytest.fixture
    def graph_config(self, graph_path):
        """Parsed graph.yaml."""
        return yaml.safe_load(graph_path.read_text())

    def test_graph_yaml_exists(self, graph_path):
        """graph.yaml should exist."""
        assert graph_path.exists()

    def test_graph_version(self, graph_config):
        """Should declare version 1.0."""
        assert graph_config["version"] == "1.0"

    def test_graph_has_state_fields(self, graph_config):
        """Should define input, echo, validation, response state fields."""
        state = graph_config["state"]
        for field in ["input", "echo", "validation", "response"]:
            assert field in state, f"State missing field: {field}"

    def test_graph_has_tool_definitions(self, graph_config):
        """Should define echo_input and validate_input tools."""
        tools = graph_config["tools"]
        assert "echo_input" in tools
        assert "validate_input" in tools
        assert tools["echo_input"]["type"] == "python"
        assert tools["validate_input"]["type"] == "python"

    def test_graph_has_correct_nodes(self, graph_config):
        """Should have echo, validate, respond nodes."""
        nodes = graph_config["nodes"]
        assert "echo" in nodes
        assert "validate" in nodes
        assert "respond" in nodes

    def test_respond_is_llm_node(self, graph_config):
        """respond node should be an LLM node."""
        assert graph_config["nodes"]["respond"]["type"] == "llm"

    def test_graph_edges_flow(self, graph_config):
        """Should flow START → echo → validate → respond → END."""
        edges = graph_config["edges"]
        edge_pairs = [(e["from"], e["to"]) for e in edges]

        assert ("START", "echo") in edge_pairs
        assert ("echo", "validate") in edge_pairs
        assert ("validate", "respond") in edge_pairs
        assert ("respond", "END") in edge_pairs

    def test_tool_modules_importable(self, graph_config):
        """Tool module paths should be valid Python imports."""
        for tool_name, tool_config in graph_config["tools"].items():
            module = tool_config["module"]
            function = tool_config["function"]
            # Verify the module string is a valid dotted path
            assert "." in module, f"Module {module} should be a dotted path"
            assert (
                function == tool_name
            ), f"Function {function} should match tool name {tool_name}"

    def test_prompt_yaml_exists(self):
        """Prompt file referenced by graph should exist."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "respond.yaml"
        assert prompt_path.exists(), f"Prompt not found at {prompt_path}"
