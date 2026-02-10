"""Tests for state expression resolution."""

import pytest
from pydantic import BaseModel

from yamlgraph.utils.expressions import (
    resolve_state_expression,
    resolve_state_path,
    resolve_template,
)


class TestResolveStateExpression:
    """Tests for resolve_state_expression function."""

    @pytest.mark.req("REQ-YG-013")
    def test_simple_key(self):
        """Resolve simple state key."""
        state = {"name": "test"}
        result = resolve_state_expression("{name}", state)
        assert result == "test"

    @pytest.mark.req("REQ-YG-013")
    def test_nested_path(self):
        """Resolve nested path like {state.story.panels}."""
        state = {"story": {"panels": ["a", "b", "c"]}}
        result = resolve_state_expression("{state.story.panels}", state)
        assert result == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-013")
    def test_state_prefix_stripped(self):
        """The 'state.' prefix is optional and stripped."""
        state = {"story": {"title": "My Story"}}
        # With prefix
        assert resolve_state_expression("{state.story.title}", state) == "My Story"
        # Without prefix
        assert resolve_state_expression("{story.title}", state) == "My Story"

    @pytest.mark.req("REQ-YG-013")
    def test_literal_passthrough(self):
        """Non-expression strings pass through unchanged."""
        result = resolve_state_expression("literal string", {})
        assert result == "literal string"

    @pytest.mark.req("REQ-YG-013")
    def test_non_string_passthrough(self):
        """Non-string values pass through unchanged."""
        result = resolve_state_expression(42, {})
        assert result == 42

    @pytest.mark.req("REQ-YG-013")
    def test_missing_key_raises(self):
        """Missing key raises KeyError."""
        state = {"foo": "bar"}
        with pytest.raises(KeyError):
            resolve_state_expression("{missing}", state)

    @pytest.mark.req("REQ-YG-013")
    def test_missing_nested_key_raises(self):
        """Missing nested key raises KeyError."""
        state = {"story": {"title": "test"}}
        with pytest.raises(KeyError):
            resolve_state_expression("{story.panels}", state)

    @pytest.mark.req("REQ-YG-013")
    def test_deeply_nested_path(self):
        """Resolve deeply nested paths."""
        state = {"a": {"b": {"c": {"d": "deep"}}}}
        result = resolve_state_expression("{a.b.c.d}", state)
        assert result == "deep"

    @pytest.mark.req("REQ-YG-013")
    def test_list_result(self):
        """Can resolve to list values."""
        state = {"items": [1, 2, 3]}
        result = resolve_state_expression("{items}", state)
        assert result == [1, 2, 3]

    @pytest.mark.req("REQ-YG-013")
    def test_dict_result(self):
        """Can resolve to dict values."""
        state = {"config": {"key": "value"}}
        result = resolve_state_expression("{config}", state)
        assert result == {"key": "value"}

    @pytest.mark.req("REQ-YG-013")
    def test_object_attribute_access(self):
        """Can resolve object attributes (Pydantic models)."""

        class MockModel:
            def __init__(self):
                self.title = "Test Title"
                self.panels = ["panel 1", "panel 2"]

        state = {"story": MockModel()}
        result = resolve_state_expression("{state.story.panels}", state)
        assert result == ["panel 1", "panel 2"]

    @pytest.mark.req("REQ-YG-013")
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

    @pytest.mark.req("REQ-YG-013")
    def test_simple_key(self):
        """Should resolve simple key."""
        state = {"score": 0.8}
        assert resolve_state_path("score", state) == 0.8

    @pytest.mark.req("REQ-YG-013")
    def test_nested_dict_path(self):
        """Should resolve nested dict path."""
        state = {"critique": {"score": 0.9}}
        assert resolve_state_path("critique.score", state) == 0.9

    @pytest.mark.req("REQ-YG-013")
    def test_deeply_nested(self):
        """Should resolve deeply nested path."""
        state = {"a": {"b": {"c": {"d": 42}}}}
        assert resolve_state_path("a.b.c.d", state) == 42

    @pytest.mark.req("REQ-YG-013")
    def test_missing_key_returns_none(self):
        """Should return None for missing key."""
        state = {"a": 1}
        assert resolve_state_path("b", state) is None

    @pytest.mark.req("REQ-YG-013")
    def test_missing_nested_returns_none(self):
        """Should return None for missing nested path."""
        state = {"a": {"b": 1}}
        assert resolve_state_path("a.c", state) is None

    @pytest.mark.req("REQ-YG-013")
    def test_pydantic_model_attribute(self):
        """Should resolve Pydantic model attribute."""

        class Critique(BaseModel):
            score: float
            feedback: str

        state = {"critique": Critique(score=0.75, feedback="Good")}
        assert resolve_state_path("critique.score", state) == 0.75
        assert resolve_state_path("critique.feedback", state) == "Good"

    @pytest.mark.req("REQ-YG-013")
    def test_empty_path_returns_none(self):
        """Should return None for empty path."""
        assert resolve_state_path("", {"a": 1}) is None


class TestResolveTemplate:
    """Tests for resolve_template - optional resolution returning None."""

    @pytest.mark.req("REQ-YG-013")
    def test_state_template(self):
        """Should resolve {state.field} template."""
        state = {"topic": "AI"}
        assert resolve_template("{state.topic}", state) == "AI"

    @pytest.mark.req("REQ-YG-013")
    def test_nested_template(self):
        """Should resolve nested path template."""
        state = {"config": {"max_tokens": 100}}
        assert resolve_template("{state.config.max_tokens}", state) == 100

    @pytest.mark.req("REQ-YG-013")
    def test_missing_returns_none(self):
        """Should return None for missing path."""
        state = {"a": 1}
        assert resolve_template("{state.missing}", state) is None

    @pytest.mark.req("REQ-YG-013")
    def test_non_string_passthrough(self):
        """Should pass through non-string values."""
        assert resolve_template(123, {}) == 123

    @pytest.mark.req("REQ-YG-013")
    def test_non_state_template_passthrough(self):
        """Should pass through non-state templates."""
        assert resolve_template("{other.field}", {}) == "{other.field}"
        assert resolve_template("plain text", {}) == "plain text"

    @pytest.mark.req("REQ-YG-013")
    def test_pydantic_model(self):
        """Should resolve Pydantic model attribute."""

        class Draft(BaseModel):
            text: str

        state = {"draft": Draft(text="Content")}
        assert resolve_template("{state.draft.text}", state) == "Content"


class TestArithmeticExpressions:
    """Tests for arithmetic expressions in resolve_template."""

    @pytest.mark.req("REQ-YG-013")
    def test_addition_with_literal(self):
        """Should handle {state.counter + 1}."""
        state = {"counter": 5}
        result = resolve_template("{state.counter + 1}", state)
        assert result == 6

    @pytest.mark.req("REQ-YG-013")
    def test_subtraction_with_literal(self):
        """Should handle {state.value - 2}."""
        state = {"value": 10}
        result = resolve_template("{state.value - 2}", state)
        assert result == 8

    @pytest.mark.req("REQ-YG-013")
    def test_multiplication_with_literal(self):
        """Should handle {state.value * 3}."""
        state = {"value": 4}
        result = resolve_template("{state.value * 3}", state)
        assert result == 12

    @pytest.mark.req("REQ-YG-013")
    def test_division_with_literal(self):
        """Should handle {state.value / 2}."""
        state = {"value": 10}
        result = resolve_template("{state.value / 2}", state)
        assert result == 5.0

    @pytest.mark.req("REQ-YG-013")
    def test_addition_with_state_reference(self):
        """Should handle {state.a + state.b}."""
        state = {"a": 3, "b": 7}
        result = resolve_template("{state.a + state.b}", state)
        assert result == 10

    @pytest.mark.req("REQ-YG-013")
    def test_list_concatenation_with_list(self):
        """Should handle {state.history + [state.item]}."""
        state = {"history": ["a", "b"], "item": "c"}
        result = resolve_template("{state.history + [state.item]}", state)
        assert result == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-013")
    def test_list_addition_single_item(self):
        """Should handle adding single item to list."""
        from yamlgraph.utils.expressions import _apply_operator

        result = _apply_operator(["a", "b"], "+", "c")
        assert result == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-013")
    def test_missing_state_returns_none(self):
        """Should return None if state path missing."""
        state = {"other": 1}
        result = resolve_template("{state.missing + 1}", state)
        assert result is None


class TestParseOperand:
    """Tests for _parse_operand helper."""

    @pytest.mark.req("REQ-YG-013")
    def test_parse_list_literal_with_state_ref(self):
        """Should parse [state.item] to list."""
        from yamlgraph.utils.expressions import _parse_operand

        state = {"item": "value"}
        result = _parse_operand("[state.item]", state)
        assert result == ["value"]

    @pytest.mark.req("REQ-YG-013")
    def test_parse_list_literal_with_literal(self):
        """Should parse literal value in list."""
        from yamlgraph.utils.expressions import _parse_operand

        result = _parse_operand("[42]", {})
        assert result == [42]

    @pytest.mark.req("REQ-YG-013")
    def test_parse_dict_literal_with_state_ref(self):
        """Should parse dict with state reference."""
        from yamlgraph.utils.expressions import _parse_operand

        state = {"name": "test"}
        result = _parse_operand("{'key': state.name}", state)
        assert result == {"key": "test"}

    @pytest.mark.req("REQ-YG-013")
    def test_parse_dict_literal_with_literal(self):
        """Should parse dict with literal value."""
        from yamlgraph.utils.expressions import _parse_operand

        result = _parse_operand("{'count': 5}", {})
        assert result == {"count": 5}


class TestParseLiteral:
    """Tests for _parse_literal helper."""

    @pytest.mark.req("REQ-YG-013")
    def test_parse_true(self):
        """Should parse 'true' as True."""
        from yamlgraph.utils.expressions import _parse_literal

        assert _parse_literal("true") is True
        assert _parse_literal("True") is True
        assert _parse_literal("TRUE") is True

    @pytest.mark.req("REQ-YG-013")
    def test_parse_false(self):
        """Should parse 'false' as False."""
        from yamlgraph.utils.expressions import _parse_literal

        assert _parse_literal("false") is False
        assert _parse_literal("False") is False

    @pytest.mark.req("REQ-YG-013")
    def test_parse_null(self):
        """Should parse 'null' and 'none' as None."""
        from yamlgraph.utils.expressions import _parse_literal

        assert _parse_literal("null") is None
        assert _parse_literal("none") is None
        assert _parse_literal("None") is None

    @pytest.mark.req("REQ-YG-013")
    def test_parse_float(self):
        """Should parse float strings."""
        from yamlgraph.utils.expressions import _parse_literal

        assert _parse_literal("3.14") == 3.14
        assert _parse_literal("0.5") == 0.5

    @pytest.mark.req("REQ-YG-013")
    def test_parse_int(self):
        """Should parse integer strings."""
        from yamlgraph.utils.expressions import _parse_literal

        assert _parse_literal("42") == 42
        assert _parse_literal("-10") == -10

    @pytest.mark.req("REQ-YG-013")
    def test_parse_quoted_string(self):
        """Should strip quotes from strings."""
        from yamlgraph.utils.expressions import _parse_literal

        assert _parse_literal('"hello"') == "hello"
        assert _parse_literal("'world'") == "world"

    @pytest.mark.req("REQ-YG-013")
    def test_parse_unquoted_string(self):
        """Should return unquoted non-numeric strings as-is."""
        from yamlgraph.utils.expressions import _parse_literal

        assert _parse_literal("hello") == "hello"


class TestApplyOperator:
    """Tests for _apply_operator helper."""

    @pytest.mark.req("REQ-YG-013")
    def test_unknown_operator_raises(self):
        """Should raise for unknown operator."""
        from yamlgraph.utils.expressions import _apply_operator

        with pytest.raises(ValueError, match="Unknown operator"):
            _apply_operator(1, "%", 2)
