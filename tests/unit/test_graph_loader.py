"""Tests for YAML graph loader.

TDD: Write tests first, then implement graph_loader.py.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Will fail until graph_loader.py is created
from showcase.graph_loader import (
    GraphConfig,
    load_graph_config,
    resolve_class,
    resolve_template,
    create_node_function,
    compile_graph,
    load_and_compile,
)
from showcase.models import GeneratedContent, Analysis, ShowcaseState


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

state_class: showcase.models.ShowcaseState

defaults:
  provider: mistral
  temperature: 0.7

nodes:
  generate:
    type: llm
    prompt: generate
    output_model: showcase.models.GeneratedContent
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


@pytest.fixture
def sample_state():
    """Sample pipeline state."""
    return ShowcaseState(
        thread_id="test-123",
        topic="machine learning",
        style="informative",
        word_count=300,
        generated=None,
        analysis=None,
        final_summary=None,
        current_step="init",
        error=None,
        errors=[],
    )


@pytest.fixture
def state_with_generated(sample_state):
    """State with generated content."""
    state = dict(sample_state)
    state["generated"] = GeneratedContent(
        title="Test Title",
        content="Test content about ML.",
        word_count=50,
        tags=["test"],
    )
    return state


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
        """State class path parsed."""
        assert sample_config.state_class == "showcase.models.ShowcaseState"


# =============================================================================
# TestResolveClass
# =============================================================================


class TestResolveClass:
    """Tests for dynamic class importing."""

    def test_resolve_existing_class(self):
        """Import a real class from dotted path."""
        cls = resolve_class("showcase.models.GeneratedContent")
        assert cls is GeneratedContent

    def test_resolve_state_class(self):
        """Import ShowcaseState."""
        cls = resolve_class("showcase.models.ShowcaseState")
        # ShowcaseState is a TypedDict, check it exists
        assert cls is not None

    def test_resolve_invalid_module_raises(self):
        """Invalid module raises ImportError."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            resolve_class("nonexistent.module.Class")

    def test_resolve_invalid_class_raises(self):
        """Invalid class name raises AttributeError."""
        with pytest.raises(AttributeError):
            resolve_class("showcase.models.NonexistentClass")


# =============================================================================
# TestResolveTemplate
# =============================================================================


class TestResolveTemplate:
    """Tests for template resolution against state."""

    def test_simple_state_access(self, sample_state):
        """'{state.topic}' resolves to state['topic']."""
        result = resolve_template("{state.topic}", sample_state)
        assert result == "machine learning"

    def test_nested_state_access(self, state_with_generated):
        """'{state.generated.content}' resolves nested attrs."""
        result = resolve_template("{state.generated.content}", state_with_generated)
        assert result == "Test content about ML."

    def test_missing_state_returns_none(self, sample_state):
        """Missing state key returns None."""
        result = resolve_template("{state.generated.content}", sample_state)
        assert result is None

    def test_literal_string_unchanged(self, sample_state):
        """Non-template strings returned as-is."""
        result = resolve_template("literal value", sample_state)
        assert result == "literal value"

    def test_int_access(self, sample_state):
        """Integer values resolved correctly."""
        result = resolve_template("{state.word_count}", sample_state)
        assert result == 300

    def test_list_access(self, state_with_generated):
        """List values resolved correctly."""
        result = resolve_template("{state.generated.tags}", state_with_generated)
        assert result == ["test"]


# =============================================================================
# TestCreateNodeFunction
# =============================================================================


class TestCreateNodeFunction:
    """Tests for node function factory."""

    def test_node_calls_execute_prompt(self, sample_state):
        """Generated node calls execute_prompt with config."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "output_model": "showcase.models.GeneratedContent",
            "temperature": 0.8,
            "variables": {"topic": "{state.topic}"},
            "state_key": "generated",
        }
        
        mock_result = GeneratedContent(
            title="Test",
            content="Content",
            word_count=100,
            tags=[],
        )
        
        with patch("showcase.graph_loader.execute_prompt", return_value=mock_result) as mock:
            node_fn = create_node_function("generate", node_config, {"provider": "mistral"})
            result = node_fn(sample_state)
            
            mock.assert_called_once()
            call_kwargs = mock.call_args
            assert call_kwargs[1]["prompt_name"] == "generate"
            assert call_kwargs[1]["temperature"] == 0.8
            assert call_kwargs[1]["variables"]["topic"] == "machine learning"
        
        assert result["generated"] == mock_result
        assert result["current_step"] == "generate"

    def test_node_checks_requirements(self, sample_state):
        """Node returns error if requires not met."""
        node_config = {
            "type": "llm",
            "prompt": "analyze",
            "variables": {},
            "state_key": "analysis",
            "requires": ["generated"],  # generated is None in sample_state
        }
        
        node_fn = create_node_function("analyze", node_config, {})
        result = node_fn(sample_state)
        
        assert result.get("error") is not None
        assert "generated" in result["error"].message

    def test_node_handles_exception(self, sample_state):
        """Exceptions become PipelineError."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "variables": {"topic": "{state.topic}"},
            "state_key": "generated",
        }
        
        with patch("showcase.graph_loader.execute_prompt", side_effect=ValueError("API Error")):
            node_fn = create_node_function("generate", node_config, {})
            result = node_fn(sample_state)
        
        assert result.get("error") is not None
        assert "API Error" in result["error"].message

    def test_node_uses_defaults(self, sample_state):
        """Node uses default provider/temperature from config."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "variables": {},
            "state_key": "generated",
            # No temperature specified - should use default
        }
        defaults = {"provider": "anthropic", "temperature": 0.5}
        
        mock_result = GeneratedContent(title="T", content="C", word_count=1, tags=[])
        
        with patch("showcase.graph_loader.execute_prompt", return_value=mock_result) as mock:
            node_fn = create_node_function("generate", node_config, defaults)
            node_fn(sample_state)
            
            assert mock.call_args[1]["temperature"] == 0.5
            assert mock.call_args[1]["provider"] == "anthropic"


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
        """START edge sets entry point."""
        graph = compile_graph(sample_config)
        
        # Entry point is tracked internally
        # We can verify by checking the graph structure
        assert graph._entry_point == "generate"

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

    def test_load_and_compile_showcase(self):
        """Load the actual showcase.yaml and compile it."""
        from showcase.config import PROJECT_ROOT
        
        showcase_path = PROJECT_ROOT / "graphs" / "showcase.yaml"
        if not showcase_path.exists():
            pytest.skip("showcase.yaml not created yet")
        
        graph = load_and_compile(showcase_path)
        compiled = graph.compile()
        
        assert compiled is not None

    def test_compiled_graph_invocable(self, sample_yaml_file):
        """Compiled graph can be invoked with initial state."""
        mock_result = GeneratedContent(
            title="Test",
            content="Content",
            word_count=100,
            tags=[],
        )
        
        with patch("showcase.graph_loader.execute_prompt", return_value=mock_result):
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
