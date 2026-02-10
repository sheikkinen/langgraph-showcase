"""Tests for node factory - class resolution, template resolution, and node creation.

Split from test_graph_loader.py for better organization and file size management.
"""

from unittest.mock import patch

import pytest

from tests.conftest import FixtureGeneratedContent
from yamlgraph.node_factory import create_node_function, resolve_class
from yamlgraph.utils.expressions import resolve_template

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_state():
    """Sample pipeline state."""
    return {
        "thread_id": "test-123",
        "topic": "machine learning",
        "style": "informative",
        "word_count": 300,
        "generated": None,
        "analysis": None,
        "final_summary": None,
        "current_step": "init",
        "error": None,
        "errors": [],
    }


@pytest.fixture
def state_with_generated(sample_state):
    """State with generated content."""
    state = dict(sample_state)
    state["generated"] = FixtureGeneratedContent(
        title="Test Title",
        content="Test content about ML.",
        word_count=50,
        tags=["test"],
    )
    return state


# =============================================================================
# TestResolveClass
# =============================================================================


class TestResolveClass:
    """Tests for dynamic class importing."""

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_resolve_existing_class(self):
        """Import a real class from dotted path."""
        cls = resolve_class("yamlgraph.models.GenericReport")
        # Just verify it resolves to a class with expected attributes
        assert cls is not None
        assert hasattr(cls, "model_fields")  # Pydantic model check

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_resolve_state_class(self):
        """Dynamic state class can be built."""
        from yamlgraph.models.state_builder import build_state_class

        cls = build_state_class({"nodes": {}})
        # Dynamic state is a TypedDict
        assert cls is not None
        assert hasattr(cls, "__annotations__")

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_resolve_invalid_module_raises(self):
        """Invalid module raises ImportError."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            resolve_class("nonexistent.module.Class")

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_resolve_invalid_class_raises(self):
        """Invalid class name raises AttributeError."""
        with pytest.raises(AttributeError):
            resolve_class("yamlgraph.models.NonexistentClass")


# =============================================================================
# TestResolveTemplate
# =============================================================================


class TestResolveTemplate:
    """Tests for template resolution against state."""

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_simple_state_access(self, sample_state):
        """'{state.topic}' resolves to state['topic']."""
        result = resolve_template("{state.topic}", sample_state)
        assert result == "machine learning"

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_nested_state_access(self, state_with_generated):
        """'{state.generated.content}' resolves nested attrs."""
        result = resolve_template("{state.generated.content}", state_with_generated)
        assert result == "Test content about ML."

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_missing_state_returns_none(self, sample_state):
        """Missing state key returns None."""
        result = resolve_template("{state.generated.content}", sample_state)
        assert result is None

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_literal_string_unchanged(self, sample_state):
        """Non-template strings returned as-is."""
        result = resolve_template("literal value", sample_state)
        assert result == "literal value"

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_int_access(self, sample_state):
        """Integer values resolved correctly."""
        result = resolve_template("{state.word_count}", sample_state)
        assert result == 300

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_list_access(self, state_with_generated):
        """List values resolved correctly."""
        result = resolve_template("{state.generated.tags}", state_with_generated)
        assert result == ["test"]


# =============================================================================
# TestCreateNodeFunction
# =============================================================================


class TestCreateNodeFunction:
    """Tests for node function factory."""

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_node_calls_execute_prompt(self, sample_state):
        """Generated node calls execute_prompt with config."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "output_model": "yamlgraph.models.GenericReport",
            "temperature": 0.8,
            "variables": {"topic": "{state.topic}"},
            "state_key": "generated",
        }

        mock_result = FixtureGeneratedContent(
            title="Test",
            content="Content",
            word_count=100,
            tags=[],
        )

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", return_value=mock_result
        ) as mock:
            node_fn = create_node_function(
                "generate", node_config, {"provider": "mistral"}
            )
            result = node_fn(sample_state)

            mock.assert_called_once()
            call_kwargs = mock.call_args
            assert call_kwargs[1]["prompt_name"] == "generate"
            assert call_kwargs[1]["temperature"] == 0.8
            assert call_kwargs[1]["variables"]["topic"] == "machine learning"

        assert result["generated"] == mock_result
        assert result["current_step"] == "generate"

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
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

        assert result.get("errors")
        assert "generated" in result["errors"][0].message

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_node_handles_exception(self, sample_state):
        """Exceptions become PipelineError."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "variables": {"topic": "{state.topic}"},
            "state_key": "generated",
        }

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt",
            side_effect=ValueError("API Error"),
        ):
            node_fn = create_node_function("generate", node_config, {})
            result = node_fn(sample_state)

        assert result.get("errors")
        assert "API Error" in result["errors"][0].message

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
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

        mock_result = FixtureGeneratedContent(
            title="T", content="C", word_count=1, tags=[]
        )

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", return_value=mock_result
        ) as mock:
            node_fn = create_node_function("generate", node_config, defaults)
            node_fn(sample_state)

            assert mock.call_args[1]["temperature"] == 0.5
            assert mock.call_args[1]["provider"] == "anthropic"

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_node_uses_graph_relative_prompts(self, sample_state, tmp_path):
        """Node uses graph_path for relative prompt resolution."""

        # Create colocated graph+prompts structure
        graph_dir = tmp_path / "questionnaires" / "audit"
        prompts_dir = graph_dir / "prompts"
        prompts_dir.mkdir(parents=True)

        graph_file = graph_dir / "graph.yaml"
        graph_file.write_text("name: audit")

        prompt_file = prompts_dir / "opening.yaml"
        prompt_file.write_text("system: Welcome\nuser: Start")

        node_config = {
            "type": "llm",
            "prompt": "prompts/opening",
            "variables": {},
            "state_key": "opening",
        }
        defaults = {"prompts_relative": True}

        mock_result = FixtureGeneratedContent(
            title="T", content="C", word_count=1, tags=[]
        )

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", return_value=mock_result
        ) as mock:
            node_fn = create_node_function(
                "generate_opening",
                node_config,
                defaults,
                graph_path=graph_file,
            )
            result = node_fn(sample_state)

            # Prompt should have been resolved
            mock.assert_called_once()
            assert result["opening"] == mock_result

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_node_uses_explicit_prompts_dir(self, sample_state, tmp_path):
        """Node uses explicit prompts_dir from defaults."""

        # Create explicit prompts directory
        shared_prompts = tmp_path / "shared" / "prompts"
        shared_prompts.mkdir(parents=True)

        prompt_file = shared_prompts / "greet.yaml"
        prompt_file.write_text("system: Hi\nuser: Hello")

        node_config = {
            "type": "llm",
            "prompt": "greet",
            "variables": {},
            "state_key": "greeting",
        }
        defaults = {"prompts_dir": str(shared_prompts)}

        mock_result = FixtureGeneratedContent(
            title="T", content="C", word_count=1, tags=[]
        )

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", return_value=mock_result
        ) as mock:
            node_fn = create_node_function(
                "greet",
                node_config,
                defaults,
            )
            result = node_fn(sample_state)

            mock.assert_called_once()
            assert result["greeting"] == mock_result

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_node_parse_json_enabled(self, sample_state):
        """Node with parse_json: true extracts JSON from response."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "variables": {},
            "state_key": "extracted",
            "parse_json": True,
        }

        # Simulate LLM returning JSON in markdown
        mock_result = """```json
{"name": "test", "value": 42}
```

Reasoning: I extracted the name and value.
"""
        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", return_value=mock_result
        ):
            node_fn = create_node_function("extract", node_config, {})
            result = node_fn(sample_state)

        # Should be parsed dict, not raw string
        assert result["extracted"] == {"name": "test", "value": 42}

    @pytest.mark.req("REQ-YG-009", "REQ-YG-045")
    def test_node_parse_json_disabled_by_default(self, sample_state):
        """Node without parse_json returns raw string."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "variables": {},
            "state_key": "raw",
            # parse_json not specified - defaults to False
        }

        mock_result = '{"key": "value"}'

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt", return_value=mock_result
        ):
            node_fn = create_node_function("raw_node", node_config, {})
            result = node_fn(sample_state)

        # Should be raw string (though it's valid JSON, we don't auto-parse)
        assert result["raw"] == '{"key": "value"}'
