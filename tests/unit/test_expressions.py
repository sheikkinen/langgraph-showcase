"""Tests for state expression resolution."""

import pytest
from pydantic import BaseModel

from showcase.utils.expressions import (
    resolve_state_expression,
    resolve_state_path,
    resolve_template,
)


class TestResolveStateExpression:
    """Tests for resolve_state_expression function."""

    def test_simple_key(self):
        """Resolve simple state key."""
        state = {"name": "test"}
        result = resolve_state_expression("{name}", state)
        assert result == "test"

    def test_nested_path(self):
        """Resolve nested path like {state.story.panels}."""
        state = {"story": {"panels": ["a", "b", "c"]}}
        result = resolve_state_expression("{state.story.panels}", state)
        assert result == ["a", "b", "c"]

    def test_state_prefix_stripped(self):
        """The 'state.' prefix is optional and stripped."""
        state = {"story": {"title": "My Story"}}
        # With prefix
        assert resolve_state_expression("{state.story.title}", state) == "My Story"
        # Without prefix
        assert resolve_state_expression("{story.title}", state) == "My Story"

    def test_literal_passthrough(self):
        """Non-expression strings pass through unchanged."""
        result = resolve_state_expression("literal string", {})
        assert result == "literal string"

    def test_non_string_passthrough(self):
        """Non-string values pass through unchanged."""
        result = resolve_state_expression(42, {})
        assert result == 42

    def test_missing_key_raises(self):
        """Missing key raises KeyError."""
        state = {"foo": "bar"}
        with pytest.raises(KeyError):
            resolve_state_expression("{missing}", state)

    def test_missing_nested_key_raises(self):
        """Missing nested key raises KeyError."""
        state = {"story": {"title": "test"}}
        with pytest.raises(KeyError):
            resolve_state_expression("{story.panels}", state)

    def test_deeply_nested_path(self):
        """Resolve deeply nested paths."""
        state = {"a": {"b": {"c": {"d": "deep"}}}}
        result = resolve_state_expression("{a.b.c.d}", state)
        assert result == "deep"

    def test_list_result(self):
        """Can resolve to list values."""
        state = {"items": [1, 2, 3]}
        result = resolve_state_expression("{items}", state)
        assert result == [1, 2, 3]

    def test_dict_result(self):
        """Can resolve to dict values."""
        state = {"config": {"key": "value"}}
        result = resolve_state_expression("{config}", state)
        assert result == {"key": "value"}

    def test_object_attribute_access(self):
        """Can resolve object attributes (Pydantic models)."""

        class MockModel:
            def __init__(self):
                self.title = "Test Title"
                self.panels = ["panel 1", "panel 2"]

        state = {"story": MockModel()}
        result = resolve_state_expression("{state.story.panels}", state)
        assert result == ["panel 1", "panel 2"]

    def test_mixed_dict_and_object_access(self):
        """Can resolve mixed dict and object paths."""

        class Inner:
            def __init__(self):
                self.value = "found"

        state = {"outer": {"middle": Inner()}}
        result = resolve_state_expression("{outer.middle.value}", state)
        assert result == "found"


class TestResolveStatePath:
    """Tests for resolve_state_path - the core resolution function."""

    def test_simple_key(self):
        """Should resolve simple key."""
        state = {"score": 0.8}
        assert resolve_state_path("score", state) == 0.8

    def test_nested_dict_path(self):
        """Should resolve nested dict path."""
        state = {"critique": {"score": 0.9}}
        assert resolve_state_path("critique.score", state) == 0.9

    def test_deeply_nested(self):
        """Should resolve deeply nested path."""
        state = {"a": {"b": {"c": {"d": 42}}}}
        assert resolve_state_path("a.b.c.d", state) == 42

    def test_missing_key_returns_none(self):
        """Should return None for missing key."""
        state = {"a": 1}
        assert resolve_state_path("b", state) is None

    def test_missing_nested_returns_none(self):
        """Should return None for missing nested path."""
        state = {"a": {"b": 1}}
        assert resolve_state_path("a.c", state) is None

    def test_pydantic_model_attribute(self):
        """Should resolve Pydantic model attribute."""

        class Critique(BaseModel):
            score: float
            feedback: str

        state = {"critique": Critique(score=0.75, feedback="Good")}
        assert resolve_state_path("critique.score", state) == 0.75
        assert resolve_state_path("critique.feedback", state) == "Good"

    def test_empty_path_returns_none(self):
        """Should return None for empty path."""
        assert resolve_state_path("", {"a": 1}) is None


class TestResolveTemplate:
    """Tests for resolve_template - optional resolution returning None."""

    def test_state_template(self):
        """Should resolve {state.field} template."""
        state = {"topic": "AI"}
        assert resolve_template("{state.topic}", state) == "AI"

    def test_nested_template(self):
        """Should resolve nested path template."""
        state = {"config": {"max_tokens": 100}}
        assert resolve_template("{state.config.max_tokens}", state) == 100

    def test_missing_returns_none(self):
        """Should return None for missing path."""
        state = {"a": 1}
        assert resolve_template("{state.missing}", state) is None

    def test_non_string_passthrough(self):
        """Should pass through non-string values."""
        assert resolve_template(123, {}) == 123

    def test_non_state_template_passthrough(self):
        """Should pass through non-state templates."""
        assert resolve_template("{other.field}", {}) == "{other.field}"
        assert resolve_template("plain text", {}) == "plain text"

    def test_pydantic_model(self):
        """Should resolve Pydantic model attribute."""

        class Draft(BaseModel):
            text: str

        state = {"draft": Draft(text="Content")}
        assert resolve_template("{state.draft.text}", state) == "Content"
