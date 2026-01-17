"""Tests for YAML graph loader.

TDD: Write tests first, then implement graph_loader.py.

Note: Node factory tests (resolve_class, resolve_template, create_node_function)
have been moved to test_node_factory.py for better organization.
"""

from unittest.mock import patch

import pytest

from tests.conftest import FixtureGeneratedContent
from yamlgraph.graph_loader import (
    GraphConfig,
    compile_graph,
    load_and_compile,
    load_graph_config,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_yaml_content():
    """Minimal valid YAML config."""
    return """
version: "1.0"
name: test_graph
description: Test pipeline

defaults:
  provider: mistral
  temperature: 0.7

nodes:
  generate:
    type: llm
    prompt: generate
    output_model: yamlgraph.models.GenericReport
    temperature: 0.8
    variables:
      topic: "{state.topic}"
    state_key: generated

edges:
  - from: START
    to: generate
  - from: generate
    to: END
"""


@pytest.fixture
def sample_yaml_file(tmp_path, sample_yaml_content):
    """Create a temporary YAML file."""
    yaml_file = tmp_path / "test_graph.yaml"
    yaml_file.write_text(sample_yaml_content)
    return yaml_file


@pytest.fixture
def sample_config(sample_yaml_file):
    """Load sample config."""
    return load_graph_config(sample_yaml_file)


# =============================================================================
# TestLoadGraphConfig
# =============================================================================


class TestLoadGraphConfig:
    """Tests for loading YAML graph configs."""

    def test_load_valid_yaml(self, sample_yaml_file):
        """Load a valid graph YAML file."""
        config = load_graph_config(sample_yaml_file)

        assert isinstance(config, GraphConfig)
        assert config.name == "test_graph"
        assert config.version == "1.0"

    def test_load_missing_file_raises(self, tmp_path):
        """FileNotFoundError for missing file."""
        missing = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_graph_config(missing)

    def test_parse_nodes(self, sample_config):
        """Nodes parsed with correct attributes."""
        assert "generate" in sample_config.nodes

        node = sample_config.nodes["generate"]
        assert node["type"] == "llm"
        assert node["prompt"] == "generate"
        assert node["temperature"] == 0.8

    def test_parse_edges(self, sample_config):
        """Edges parsed correctly."""
        assert len(sample_config.edges) == 2
        assert sample_config.edges[0]["from"] == "START"
        assert sample_config.edges[0]["to"] == "generate"

    def test_parse_defaults(self, sample_config):
        """Defaults parsed correctly."""
        assert sample_config.defaults["provider"] == "mistral"
        assert sample_config.defaults["temperature"] == 0.7

    def test_parse_state_class(self, sample_config):
        """State class defaults to empty (dynamic generation)."""
        assert sample_config.state_class == ""


# =============================================================================
# TestCompileGraph
# =============================================================================


class TestCompileGraph:
    """Tests for compiling config to LangGraph."""

    def test_graph_has_all_nodes(self, sample_config):
        """Compiled graph contains all defined nodes."""
        graph = compile_graph(sample_config)

        # Check node was added (nodes are stored in graph.nodes)
        assert "generate" in graph.nodes

    def test_entry_point_set(self, sample_config):
        """START edge sets entry point correctly."""
        graph = compile_graph(sample_config)

        # Verify entry point by checking the graph compiles and
        # the first node is reachable from START
        compiled = graph.compile()
        assert compiled is not None

        # The 'generate' node should be in the graph
        assert "generate" in graph.nodes

    def test_edges_connected(self, sample_config):
        """Edges create correct topology."""
        graph = compile_graph(sample_config)

        # Compile to check it works
        compiled = graph.compile()
        assert compiled is not None


# =============================================================================
# TestLoadAndCompile
# =============================================================================


class TestLoadAndCompile:
    """Integration tests for full load-compile flow."""

    def test_load_and_compile_yamlgraph(self):
        """Load the actual yamlgraph.yaml and compile it."""
        from yamlgraph.config import PROJECT_ROOT

        yamlgraph_path = PROJECT_ROOT / "graphs" / "yamlgraph.yaml"
        if not yamlgraph_path.exists():
            pytest.skip("yamlgraph.yaml not created yet")

        graph = load_and_compile(yamlgraph_path)
        compiled = graph.compile()

        assert compiled is not None

    def test_compiled_graph_invocable(self, sample_yaml_file):
        """Compiled graph can be invoked with initial state."""
        mock_result = FixtureGeneratedContent(
            title="Test",
            content="Content",
            word_count=100,
            tags=[],
        )

        with patch("yamlgraph.node_factory.execute_prompt", return_value=mock_result):
            graph = load_and_compile(sample_yaml_file)
            compiled = graph.compile()

            initial_state = {
                "thread_id": "test",
                "topic": "AI",
                "style": "casual",
                "word_count": 100,
            }

            result = compiled.invoke(initial_state)

            assert result.get("generated") is not None
            assert result["generated"].title == "Test"


# =============================================================================
# TestYAMLSchemaValidation
# =============================================================================


class TestYAMLSchemaValidation:
    """Tests for YAML schema validation on load."""

    def test_missing_nodes_raises_error(self, tmp_path):
        """YAML without nodes should raise ValidationError."""
        yaml_content = """
version: "1.0"
name: empty_graph
edges:
  - from: START
    to: END
"""
        yaml_file = tmp_path / "no_nodes.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="nodes"):
            load_graph_config(yaml_file)

    def test_missing_edges_raises_error(self, tmp_path):
        """YAML without edges should raise ValidationError."""
        yaml_content = """
version: "1.0"
name: no_edges
nodes:
  generate:
    type: llm
    prompt: generate
"""
        yaml_file = tmp_path / "no_edges.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="edges"):
            load_graph_config(yaml_file)

    def test_node_missing_prompt_raises_error(self, tmp_path):
        """Node without prompt should raise ValidationError."""
        yaml_content = """
version: "1.0"
name: bad_node
nodes:
  generate:
    type: llm
    output_model: yamlgraph.models.GenericReport
edges:
  - from: START
    to: generate
"""
        yaml_file = tmp_path / "no_prompt.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="prompt"):
            load_graph_config(yaml_file)

    def test_edge_missing_from_raises_error(self, tmp_path):
        """Edge without 'from' should raise ValidationError."""
        yaml_content = """
version: "1.0"
name: bad_edge
nodes:
  generate:
    type: llm
    prompt: generate
edges:
  - to: generate
"""
        yaml_file = tmp_path / "no_from.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="from"):
            load_graph_config(yaml_file)

    def test_edge_missing_to_raises_error(self, tmp_path):
        """Edge without 'to' should raise ValidationError."""
        yaml_content = """
version: "1.0"
name: bad_edge
nodes:
  generate:
    type: llm
    prompt: generate
edges:
  - from: START
"""
        yaml_file = tmp_path / "no_to.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValueError, match="to"):
            load_graph_config(yaml_file)

    def test_valid_yaml_passes_validation(self, sample_yaml_file):
        """Valid YAML should load without errors."""
        config = load_graph_config(sample_yaml_file)
        assert config.name == "test_graph"
        assert "generate" in config.nodes
