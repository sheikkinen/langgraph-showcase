"""Tests for node factory - class resolution, template resolution, and node creation.

Split from test_graph_loader.py for better organization and file size management.
"""

import pytest
from unittest.mock import patch

from showcase.node_factory import (
    create_node_function,
    resolve_class,
    resolve_template,
)
from showcase.models import ShowcaseState
from tests.conftest import FixtureGeneratedContent


# =============================================================================
# Fixtures
# =============================================================================


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

    def test_resolve_existing_class(self):
        """Import a real class from dotted path."""
        cls = resolve_class("showcase.models.GenericReport")
        # Just verify it resolves to a class with expected attributes
        assert cls is not None
        assert hasattr(cls, "model_fields")  # Pydantic model check

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
            "output_model": "showcase.models.GenericReport",
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
            "showcase.node_factory.execute_prompt", return_value=mock_result
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

        with patch(
            "showcase.node_factory.execute_prompt", side_effect=ValueError("API Error")
        ):
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

        mock_result = FixtureGeneratedContent(
            title="T", content="C", word_count=1, tags=[]
        )

        with patch(
            "showcase.node_factory.execute_prompt", return_value=mock_result
        ) as mock:
            node_fn = create_node_function("generate", node_config, defaults)
            node_fn(sample_state)

            assert mock.call_args[1]["temperature"] == 0.5
            assert mock.call_args[1]["provider"] == "anthropic"
