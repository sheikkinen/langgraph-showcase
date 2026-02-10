"""TDD tests for the YAMLGraph Expression Language specification.

These tests verify every documented behavior of the expression language
to ensure the reference documentation (reference/expressions.md) is
grounded in verified code behavior — no assumptions.

Covers:
- Value expressions: simple paths, arithmetic, list/dict operations
- Condition expressions: comparisons, compound AND/OR, precedence
- Literal parsing: types, edge cases
- resolve_node_variables: batch resolution, filtering
- Context-specific behavior: where state. prefix is required vs optional
- Error handling: missing paths, type mismatches, division by zero
"""

import pytest
from pydantic import BaseModel

from yamlgraph.utils.conditions import (
    evaluate_comparison,
    evaluate_condition,
)
from yamlgraph.utils.expressions import (
    _apply_operator,
    _parse_operand,
    resolve_node_variables,
    resolve_state_expression,
    resolve_state_path,
    resolve_template,
)
from yamlgraph.utils.parsing import parse_literal

# ──────────────────────────────────────────────────────────
# Section 1: Path Resolution — resolve_state_path
# ──────────────────────────────────────────────────────────


class TestPathResolution:
    """Verify dotted path resolution semantics for documentation."""

    @pytest.mark.req("REQ-YG-051")
    def test_single_key(self):
        """Path 'name' resolves state['name']."""
        assert resolve_state_path("name", {"name": "Alice"}) == "Alice"

    @pytest.mark.req("REQ-YG-051")
    def test_two_level_path(self):
        """Path 'a.b' resolves state['a']['b']."""
        assert resolve_state_path("a.b", {"a": {"b": 42}}) == 42

    @pytest.mark.req("REQ-YG-051")
    def test_three_level_path(self):
        """Path 'a.b.c' resolves 3 levels deep."""
        assert resolve_state_path("a.b.c", {"a": {"b": {"c": "deep"}}}) == "deep"

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_to_list(self):
        """Path can resolve to a list value."""
        assert resolve_state_path("items", {"items": [1, 2, 3]}) == [1, 2, 3]

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_to_dict(self):
        """Path can resolve to a dict value."""
        assert resolve_state_path("config", {"config": {"k": "v"}}) == {"k": "v"}

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_to_none_value(self):
        """Path can resolve to an explicit None value."""
        assert resolve_state_path("x", {"x": None}) is None

    @pytest.mark.req("REQ-YG-051")
    def test_missing_key_returns_none(self):
        """Missing top-level key returns None (not KeyError)."""
        assert resolve_state_path("missing", {"a": 1}) is None

    @pytest.mark.req("REQ-YG-051")
    def test_missing_nested_key_returns_none(self):
        """Missing nested key returns None."""
        assert resolve_state_path("a.missing", {"a": {"b": 1}}) is None

    @pytest.mark.req("REQ-YG-051")
    def test_empty_path_returns_none(self):
        """Empty string path returns None."""
        assert resolve_state_path("", {"a": 1}) is None

    @pytest.mark.req("REQ-YG-051")
    def test_pydantic_model_attribute(self):
        """Resolves Pydantic model attributes via getattr."""

        class Score(BaseModel):
            value: float

        assert resolve_state_path("s.value", {"s": Score(value=0.9)}) == 0.9

    @pytest.mark.req("REQ-YG-051")
    def test_mixed_dict_then_object(self):
        """Dict key -> object attribute in same path."""

        class Inner:
            name = "found"

        assert (
            resolve_state_path("outer.inner.name", {"outer": {"inner": Inner()}})
            == "found"
        )

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_to_zero(self):
        """Path resolving to 0 is not confused with None/missing."""
        assert resolve_state_path("counter", {"counter": 0}) == 0

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_to_empty_string(self):
        """Path resolving to '' is not confused with None/missing."""
        assert resolve_state_path("text", {"text": ""}) == ""

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_to_false(self):
        """Path resolving to False is not confused with None/missing."""
        assert resolve_state_path("flag", {"flag": False}) is False

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_to_empty_list(self):
        """Path resolving to [] is not confused with None/missing."""
        assert resolve_state_path("items", {"items": []}) == []

    @pytest.mark.req("REQ-YG-051")
    def test_none_in_chain_stops_traversal(self):
        """If intermediate value is None, returns None instead of error."""
        assert resolve_state_path("a.b.c", {"a": None}) is None


# ──────────────────────────────────────────────────────────
# Section 2: Value Expressions — resolve_state_expression
# ──────────────────────────────────────────────────────────


class TestValueExpressions:
    """Verify {state.field} expression semantics."""

    @pytest.mark.req("REQ-YG-051")
    def test_braces_required(self):
        """Value must be wrapped in { } to be treated as expression."""
        assert resolve_state_expression("name", {"name": "Alice"}) == "name"

    @pytest.mark.req("REQ-YG-051")
    def test_state_prefix_is_optional(self):
        """{name} and {state.name} both resolve state['name']."""
        state = {"name": "Alice"}
        assert resolve_state_expression("{name}", state) == "Alice"
        assert resolve_state_expression("{state.name}", state) == "Alice"

    @pytest.mark.req("REQ-YG-051")
    def test_nested_with_prefix(self):
        """{state.a.b} resolves state['a']['b']."""
        state = {"a": {"b": "nested"}}
        assert resolve_state_expression("{state.a.b}", state) == "nested"

    @pytest.mark.req("REQ-YG-051")
    def test_nested_without_prefix(self):
        """{a.b} resolves state['a']['b'] (no prefix needed)."""
        state = {"a": {"b": "nested"}}
        assert resolve_state_expression("{a.b}", state) == "nested"

    @pytest.mark.req("REQ-YG-051")
    def test_missing_key_raises_keyerror(self):
        """Missing key raises KeyError (strict, unlike resolve_state_path)."""
        with pytest.raises(KeyError):
            resolve_state_expression("{missing}", {"a": 1})

    @pytest.mark.req("REQ-YG-051")
    def test_non_string_passthrough(self):
        """Non-string input passes through unchanged."""
        assert resolve_state_expression(42, {}) == 42
        assert resolve_state_expression(None, {}) is None
        assert resolve_state_expression([1, 2], {}) == [1, 2]

    @pytest.mark.req("REQ-YG-051")
    def test_no_braces_passthrough(self):
        """Strings without curly braces pass through unchanged."""
        assert resolve_state_expression("hello world", {}) == "hello world"

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_boolean_value(self):
        """Can resolve to boolean values."""
        assert resolve_state_expression("{flag}", {"flag": True}) is True
        assert resolve_state_expression("{flag}", {"flag": False}) is False


# ──────────────────────────────────────────────────────────
# Section 3: Template Resolution — resolve_template
# ──────────────────────────────────────────────────────────


class TestTemplateResolution:
    """Verify resolve_template semantics (used by variables: and output:)."""

    @pytest.mark.req("REQ-YG-051")
    def test_simple_path(self):
        """{state.field} resolves to state value."""
        assert resolve_template("{state.topic}", {"topic": "AI"}) == "AI"

    @pytest.mark.req("REQ-YG-051")
    def test_nested_path(self):
        """{state.a.b} resolves nested path."""
        assert resolve_template("{state.a.b}", {"a": {"b": 99}}) == 99

    @pytest.mark.req("REQ-YG-051")
    def test_missing_path_returns_none(self):
        """Missing path returns None (not KeyError, unlike resolve_state_expression)."""
        assert resolve_template("{state.missing}", {"a": 1}) is None

    @pytest.mark.req("REQ-YG-051")
    def test_non_state_prefix_returns_template_as_is(self):
        """Templates not starting with {state. are returned unchanged."""
        assert resolve_template("{other.field}", {}) == "{other.field}"

    @pytest.mark.req("REQ-YG-051")
    def test_non_string_passthrough(self):
        """Non-string values pass through unchanged."""
        assert resolve_template(42, {}) == 42
        assert resolve_template(True, {}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_no_braces_passthrough(self):
        """Plain strings without braces pass through unchanged."""
        assert resolve_template("plain text", {}) == "plain text"

    @pytest.mark.req("REQ-YG-051")
    def test_state_prefix_required_for_simple_path(self):
        """resolve_template requires state. prefix (unlike resolve_state_expression).

        {field} without state. prefix is NOT resolved — returned as-is.
        """
        result = resolve_template("{topic}", {"topic": "AI"})
        # This should NOT resolve — no state. prefix
        assert result == "{topic}"


# ──────────────────────────────────────────────────────────
# Section 4: Arithmetic Expressions
# ──────────────────────────────────────────────────────────


class TestArithmeticExpressions:
    """Verify arithmetic expression semantics."""

    @pytest.mark.req("REQ-YG-051")
    def test_add_integer_literal(self):
        """{state.counter + 1} adds 1 to state value."""
        assert resolve_template("{state.counter + 1}", {"counter": 5}) == 6

    @pytest.mark.req("REQ-YG-051")
    def test_subtract_integer_literal(self):
        """{state.value - 2} subtracts literal."""
        assert resolve_template("{state.value - 2}", {"value": 10}) == 8

    @pytest.mark.req("REQ-YG-051")
    def test_multiply_integer_literal(self):
        """{state.value * 3} multiplies."""
        assert resolve_template("{state.value * 3}", {"value": 4}) == 12

    @pytest.mark.req("REQ-YG-051")
    def test_divide_integer_literal(self):
        """{state.value / 2} divides (returns float)."""
        result = resolve_template("{state.value / 2}", {"value": 10})
        assert result == 5.0
        assert isinstance(result, float)

    @pytest.mark.req("REQ-YG-051")
    def test_add_float_literal(self):
        """{state.score + 0.1} adds float."""
        result = resolve_template("{state.score + 0.1}", {"score": 0.8})
        assert abs(result - 0.9) < 1e-9

    @pytest.mark.req("REQ-YG-051")
    def test_add_two_state_refs(self):
        """{state.a + state.b} adds two state values."""
        assert resolve_template("{state.a + state.b}", {"a": 3, "b": 7}) == 10

    @pytest.mark.req("REQ-YG-051")
    def test_subtract_two_state_refs(self):
        """{state.a - state.b} subtracts two state values."""
        assert resolve_template("{state.a - state.b}", {"a": 10, "b": 3}) == 7

    @pytest.mark.req("REQ-YG-051")
    def test_missing_left_operand_returns_none(self):
        """If left operand is missing, returns None."""
        assert resolve_template("{state.missing + 1}", {"other": 1}) is None

    @pytest.mark.req("REQ-YG-051")
    def test_left_operand_must_have_state_prefix(self):
        """Arithmetic PATTERN requires state. prefix on left operand."""
        # {counter + 1} won't match ARITHMETIC_PATTERN
        result = resolve_template("{counter + 1}", {"counter": 5})
        # Without state. prefix, it won't be recognized as arithmetic
        assert result == "{counter + 1}"

    @pytest.mark.req("REQ-YG-051")
    def test_division_by_zero_raises(self):
        """{state.value / 0} raises ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError):
            resolve_template("{state.value / 0}", {"value": 10})

    @pytest.mark.req("REQ-YG-051")
    def test_nested_left_operand(self):
        """{state.a.b + 1} with nested left operand."""
        assert resolve_template("{state.a.b + 1}", {"a": {"b": 5}}) == 6


# ──────────────────────────────────────────────────────────
# Section 5: List Operations
# ──────────────────────────────────────────────────────────


class TestListOperations:
    """Verify list expression semantics."""

    @pytest.mark.req("REQ-YG-051")
    def test_list_append_state_ref(self):
        """{state.history + [state.item]} appends item to list."""
        state = {"history": ["a", "b"], "item": "c"}
        result = resolve_template("{state.history + [state.item]}", state)
        assert result == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-051")
    def test_list_append_literal(self):
        """{state.items + [42]} appends literal to list."""
        state = {"items": [1, 2]}
        result = resolve_template("{state.items + [42]}", state)
        assert result == [1, 2, 42]

    @pytest.mark.req("REQ-YG-051")
    def test_list_plus_non_list_appends(self):
        """_apply_operator with list + scalar wraps scalar in list."""
        result = _apply_operator(["a", "b"], "+", "c")
        assert result == ["a", "b", "c"]

    @pytest.mark.req("REQ-YG-051")
    def test_list_plus_list_concatenates(self):
        """_apply_operator with list + list concatenates."""
        result = _apply_operator([1, 2], "+", [3, 4])
        assert result == [1, 2, 3, 4]

    @pytest.mark.req("REQ-YG-051")
    def test_dict_literal_appended_to_list_directly(self):
        """{state.log + {'key': state.val}} appends dict to list.

        When left operand is a list and right is a non-list (dict),
        _apply_operator wraps the right operand in a list.
        """
        state = {"log": [], "val": "test"}
        result = resolve_template("{state.log + {'key': state.val}}", state)
        assert result == [{"key": "test"}]

    @pytest.mark.req("REQ-YG-051")
    def test_dict_inside_list_literal_NOT_supported(self):
        """[{'key': state.val}] does NOT resolve — inner dict treated as string.

        This is a known limitation: list literal parser only handles
        state refs ([state.x]) or simple literals ([42]), not nested dicts.
        """
        state = {"log": [], "val": "test"}
        result = resolve_template("{state.log + [{'key': state.val}]}", state)
        # The dict literal is treated as a raw string, NOT parsed
        assert result == ["{'key': state.val}"]

    @pytest.mark.req("REQ-YG-051")
    def test_multi_item_list_literal_NOT_supported(self):
        """[state.a, state.b] does NOT parse as two items.

        List literal only supports a single item between brackets.
        """
        result = _parse_operand("[state.a, state.b]", {"a": 1, "b": 2})
        # The comma-separated content is NOT split — treated as one item
        assert result == [None]  # "state.a, state.b" doesn't start with "state."

    @pytest.mark.req("REQ-YG-051")
    def test_original_list_not_mutated(self):
        """List operations create new list, don't mutate original."""
        original = ["a", "b"]
        state = {"history": original, "item": "c"}
        resolve_template("{state.history + [state.item]}", state)
        assert original == ["a", "b"]

    @pytest.mark.req("REQ-YG-051")
    def test_empty_list_append(self):
        """Appending to empty list works."""
        state = {"items": [], "new": "first"}
        result = resolve_template("{state.items + [state.new]}", state)
        assert result == ["first"]


# ──────────────────────────────────────────────────────────
# Section 6: Dict Literal Parsing
# ──────────────────────────────────────────────────────────


class TestDictLiteralParsing:
    """Verify dict literal operand parsing."""

    @pytest.mark.req("REQ-YG-051")
    def test_single_key_state_ref(self):
        """{'key': state.value} resolves state ref."""
        result = _parse_operand("{'name': state.user}", {"user": "Alice"})
        assert result == {"name": "Alice"}

    @pytest.mark.req("REQ-YG-051")
    def test_single_key_literal(self):
        """{'count': 5} parses literal value."""
        result = _parse_operand("{'count': 5}", {})
        assert result == {"count": 5}

    @pytest.mark.req("REQ-YG-051")
    def test_multiple_keys(self):
        """{'a': state.x, 'b': state.y} with multiple keys."""
        state = {"x": "val_x", "y": "val_y"}
        result = _parse_operand("{'a': state.x, 'b': state.y}", state)
        assert result == {"a": "val_x", "b": "val_y"}

    @pytest.mark.req("REQ-YG-051")
    def test_double_quoted_keys(self):
        """Dict literal with double-quoted keys."""
        result = _parse_operand('{"key": 42}', {})
        assert result == {"key": 42}

    @pytest.mark.req("REQ-YG-051")
    def test_nested_state_ref_value(self):
        """{'score': state.a.b} with nested state ref."""
        result = _parse_operand("{'score': state.a.b}", {"a": {"b": 0.9}})
        assert result == {"score": 0.9}


# ──────────────────────────────────────────────────────────
# Section 7: List Literal Parsing
# ──────────────────────────────────────────────────────────


class TestListLiteralParsing:
    """Verify list literal operand parsing."""

    @pytest.mark.req("REQ-YG-051")
    def test_state_ref_in_list(self):
        """[state.item] resolves to [value]."""
        result = _parse_operand("[state.item]", {"item": "x"})
        assert result == ["x"]

    @pytest.mark.req("REQ-YG-051")
    def test_integer_literal_in_list(self):
        """[42] parses to [42]."""
        result = _parse_operand("[42]", {})
        assert result == [42]

    @pytest.mark.req("REQ-YG-051")
    def test_nested_state_ref_in_list(self):
        """[state.a.b] resolves nested path."""
        result = _parse_operand("[state.a.b]", {"a": {"b": "deep"}})
        assert result == ["deep"]

    @pytest.mark.req("REQ-YG-051")
    def test_string_literal_in_list(self):
        """[hello] parses as [\"hello\"]."""
        result = _parse_operand("[hello]", {})
        assert result == ["hello"]


# ──────────────────────────────────────────────────────────
# Section 8: Literal Parsing (shared by conditions + expressions)
# ──────────────────────────────────────────────────────────


class TestLiteralParsing:
    """Verify parse_literal semantics for documentation."""

    @pytest.mark.req("REQ-YG-051")
    def test_integer(self):
        assert parse_literal("42") == 42
        assert isinstance(parse_literal("42"), int)

    @pytest.mark.req("REQ-YG-051")
    def test_negative_integer(self):
        assert parse_literal("-5") == -5

    @pytest.mark.req("REQ-YG-051")
    def test_float(self):
        assert parse_literal("3.14") == 3.14
        assert isinstance(parse_literal("3.14"), float)

    @pytest.mark.req("REQ-YG-051")
    def test_negative_float(self):
        assert parse_literal("-0.5") == -0.5

    @pytest.mark.req("REQ-YG-051")
    def test_zero(self):
        assert parse_literal("0") == 0
        assert isinstance(parse_literal("0"), int)

    @pytest.mark.req("REQ-YG-051")
    def test_boolean_true_case_insensitive(self):
        assert parse_literal("true") is True
        assert parse_literal("True") is True
        assert parse_literal("TRUE") is True

    @pytest.mark.req("REQ-YG-051")
    def test_boolean_false_case_insensitive(self):
        assert parse_literal("false") is False
        assert parse_literal("False") is False
        assert parse_literal("FALSE") is False

    @pytest.mark.req("REQ-YG-051")
    def test_null(self):
        assert parse_literal("null") is None

    @pytest.mark.req("REQ-YG-051")
    def test_none_keyword(self):
        assert parse_literal("None") is None

    @pytest.mark.req("REQ-YG-051")
    def test_double_quoted_string(self):
        assert parse_literal('"hello"') == "hello"

    @pytest.mark.req("REQ-YG-051")
    def test_single_quoted_string(self):
        assert parse_literal("'world'") == "world"

    @pytest.mark.req("REQ-YG-051")
    def test_unquoted_non_numeric_string(self):
        """Unquoted non-numeric string returned as-is."""
        assert parse_literal("hello") == "hello"

    @pytest.mark.req("REQ-YG-051")
    def test_empty_quoted_string(self):
        """Empty quoted string resolves to empty string."""
        assert parse_literal('""') == ""
        assert parse_literal("''") == ""


# ──────────────────────────────────────────────────────────
# Section 9: Condition Expressions
# ──────────────────────────────────────────────────────────


class TestConditionExpressions:
    """Verify condition expression semantics for documentation."""

    # --- Single comparison ---

    @pytest.mark.req("REQ-YG-051")
    def test_less_than(self):
        assert evaluate_condition("score < 0.8", {"score": 0.5}) is True
        assert evaluate_condition("score < 0.8", {"score": 0.9}) is False

    @pytest.mark.req("REQ-YG-051")
    def test_greater_than(self):
        assert evaluate_condition("score > 0.5", {"score": 0.8}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_less_than_equal(self):
        assert evaluate_condition("count <= 5", {"count": 5}) is True
        assert evaluate_condition("count <= 5", {"count": 6}) is False

    @pytest.mark.req("REQ-YG-051")
    def test_greater_than_equal(self):
        assert evaluate_condition("count >= 5", {"count": 5}) is True
        assert evaluate_condition("count >= 5", {"count": 4}) is False

    @pytest.mark.req("REQ-YG-051")
    def test_equal_string(self):
        assert evaluate_condition("status == 'done'", {"status": "done"}) is True
        assert evaluate_condition('status == "done"', {"status": "done"}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_equal_number(self):
        assert evaluate_condition("count == 3", {"count": 3}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_equal_boolean(self):
        assert evaluate_condition("flag == true", {"flag": True}) is True
        assert evaluate_condition("flag == false", {"flag": False}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_not_equal(self):
        assert evaluate_condition("status != 'done'", {"status": "pending"}) is True
        assert evaluate_condition("status != 'done'", {"status": "done"}) is False

    # --- No state. prefix in conditions ---

    @pytest.mark.req("REQ-YG-051")
    def test_no_state_prefix_in_conditions(self):
        """Conditions use bare paths — no {state.} prefix or braces."""
        assert evaluate_condition("score < 0.8", {"score": 0.5}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_nested_path_in_condition(self):
        """Dotted paths work: critique.score >= 0.8."""
        state = {"critique": {"score": 0.9}}
        assert evaluate_condition("critique.score >= 0.8", state) is True

    @pytest.mark.req("REQ-YG-051")
    def test_deeply_nested_condition(self):
        """Three-level paths work."""
        state = {"a": {"b": {"c": 5}}}
        assert evaluate_condition("a.b.c > 3", state) is True

    # --- Missing values ---

    @pytest.mark.req("REQ-YG-051")
    def test_missing_value_comparison_returns_false(self):
        """Missing left value returns False for <, >, <=, >=."""
        assert evaluate_comparison("missing", "<", "5", {}) is False
        assert evaluate_comparison("missing", ">", "5", {}) is False
        assert evaluate_comparison("missing", "<=", "5", {}) is False
        assert evaluate_comparison("missing", ">=", "5", {}) is False

    @pytest.mark.req("REQ-YG-051")
    def test_missing_value_equals_none(self):
        """Missing value == None is True."""
        assert evaluate_comparison("missing", "==", "None", {}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_missing_value_not_equals_something(self):
        """Missing value != 'value' is True."""
        assert evaluate_comparison("missing", "!=", '"value"', {}) is True

    # --- Type mismatch ---

    @pytest.mark.req("REQ-YG-051")
    def test_type_mismatch_returns_false(self):
        """Comparing string < number returns False (caught by TypeError)."""
        assert evaluate_comparison("val", "<", "5", {"val": "text"}) is False

    # --- Compound expressions ---

    @pytest.mark.req("REQ-YG-051")
    def test_compound_and(self):
        """a > 1 and b < 10 — both must be true."""
        state = {"a": 5, "b": 3}
        assert evaluate_condition("a > 1 and b < 10", state) is True
        assert evaluate_condition("a > 1 and b > 10", state) is False

    @pytest.mark.req("REQ-YG-051")
    def test_compound_or(self):
        """a > 10 or b < 10 — either can be true."""
        state = {"a": 5, "b": 3}
        assert evaluate_condition("a > 10 or b < 10", state) is True
        assert evaluate_condition("a > 10 or b > 10", state) is False

    @pytest.mark.req("REQ-YG-051")
    def test_three_and_conditions(self):
        """Three AND conditions."""
        state = {"a": 5, "b": 3, "c": 7}
        assert evaluate_condition("a > 1 and b < 10 and c == 7", state) is True
        assert evaluate_condition("a > 1 and b < 10 and c == 8", state) is False

    @pytest.mark.req("REQ-YG-051")
    def test_three_or_conditions(self):
        """Three OR conditions."""
        state = {"a": 5, "b": 3, "c": 7}
        assert evaluate_condition("a > 10 or b > 10 or c == 7", state) is True
        assert evaluate_condition("a > 10 or b > 10 or c > 10", state) is False

    @pytest.mark.req("REQ-YG-051")
    def test_precedence_and_higher_than_or(self):
        """OR splits first (lower precedence), then AND.

        'a > 10 or b < 5 and c > 5' is parsed as:
        'a > 10' OR ('b < 5 and c > 5')
        """
        state = {"a": 1, "b": 3, "c": 7}
        # a > 10 = False
        # b < 5 and c > 5 = True and True = True
        # False or True = True
        assert evaluate_condition("a > 10 or b < 5 and c > 5", state) is True

    @pytest.mark.req("REQ-YG-051")
    def test_precedence_reverse_order(self):
        """'b < 5 and c > 5 or a > 10' — AND part first due to order.

        Splits on ' or ' first: ['b < 5 and c > 5', 'a > 10']
        Evaluates each: [True, False] -> any() -> True
        """
        state = {"a": 1, "b": 3, "c": 7}
        assert evaluate_condition("b < 5 and c > 5 or a > 10", state) is True

    # --- Case insensitivity of and/or ---

    @pytest.mark.req("REQ-YG-051")
    def test_and_case_insensitive(self):
        """'AND', 'And', 'and' all work."""
        state = {"a": 5, "b": 3}
        assert evaluate_condition("a > 1 AND b < 10", state) is True
        assert evaluate_condition("a > 1 And b < 10", state) is True

    @pytest.mark.req("REQ-YG-051")
    def test_or_case_insensitive(self):
        """'OR', 'Or', 'or' all work."""
        state = {"a": 5, "b": 3}
        assert evaluate_condition("a > 10 OR b < 10", state) is True
        assert evaluate_condition("a > 10 Or b < 10", state) is True

    # --- Whitespace ---

    @pytest.mark.req("REQ-YG-051")
    def test_leading_trailing_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        assert evaluate_condition("  score < 0.8  ", {"score": 0.5}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_no_spaces_around_operator(self):
        """Works without spaces: score<0.8."""
        assert evaluate_condition("score<0.8", {"score": 0.5}) is True

    # --- Invalid expressions ---

    @pytest.mark.req("REQ-YG-051")
    def test_invalid_expression_raises_valueerror(self):
        """Malformed expressions raise ValueError."""
        with pytest.raises(ValueError, match="Invalid condition"):
            evaluate_condition("not valid !!!", {})

    # --- No parentheses ---

    @pytest.mark.req("REQ-YG-051")
    def test_parentheses_not_supported(self):
        """Parentheses are not supported and will fail."""
        with pytest.raises(ValueError, match="Invalid condition"):
            evaluate_condition("(a > 1) and (b < 10)", {"a": 5, "b": 3})

    # --- No NOT operator ---

    @pytest.mark.req("REQ-YG-051")
    def test_not_operator_not_supported(self):
        """'not' is not supported as a unary operator."""
        with pytest.raises(ValueError, match="Invalid condition"):
            evaluate_condition("not flag == true", {"flag": True})

    # --- Pydantic model values ---

    @pytest.mark.req("REQ-YG-051")
    def test_pydantic_model_in_condition(self):
        """Conditions work with Pydantic model attributes."""

        class Critique(BaseModel):
            score: float

        state = {"critique": Critique(score=0.75)}
        assert evaluate_condition("critique.score < 0.8", state) is True


# ──────────────────────────────────────────────────────────
# Section 10: resolve_node_variables
# ──────────────────────────────────────────────────────────


class TestResolveNodeVariables:
    """Verify resolve_node_variables batch resolution semantics."""

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_templates(self):
        """Templates dict is resolved against state."""
        templates = {"name": "{state.name}", "score": "{state.score}"}
        state = {"name": "Alice", "score": 0.9}
        result = resolve_node_variables(templates, state)
        assert result == {"name": "Alice", "score": 0.9}

    @pytest.mark.req("REQ-YG-051")
    def test_resolves_arithmetic(self):
        """Arithmetic templates are resolved."""
        templates = {"next": "{state.counter + 1}"}
        state = {"counter": 5}
        result = resolve_node_variables(templates, state)
        assert result == {"next": 6}

    @pytest.mark.req("REQ-YG-051")
    def test_none_templates_returns_filtered_state(self):
        """None templates = return state without _ keys and None values."""
        state = {"name": "Alice", "_route": "x", "empty": None, "score": 0.9}
        result = resolve_node_variables(None, state)
        assert result == {"name": "Alice", "score": 0.9}

    @pytest.mark.req("REQ-YG-051")
    def test_empty_dict_templates_returns_filtered_state(self):
        """Empty dict templates = return state without _ keys and None values."""
        state = {"name": "Alice", "_route": "x", "empty": None}
        result = resolve_node_variables({}, state)
        assert result == {"name": "Alice"}

    @pytest.mark.req("REQ-YG-051")
    def test_underscore_keys_filtered(self):
        """Keys starting with _ are filtered from untemplatized state."""
        state = {"name": "Alice", "_internal": "hidden", "_route": "x"}
        result = resolve_node_variables(None, state)
        assert "_internal" not in result
        assert "_route" not in result
        assert result["name"] == "Alice"

    @pytest.mark.req("REQ-YG-051")
    def test_none_values_filtered(self):
        """None values are filtered from untemplatized state."""
        state = {"present": "yes", "absent": None}
        result = resolve_node_variables(None, state)
        assert "absent" not in result
        assert result["present"] == "yes"

    @pytest.mark.req("REQ-YG-051")
    def test_preserves_complex_types(self):
        """List and dict values are preserved through resolution."""
        templates = {"items": "{state.items}"}
        state = {"items": [{"a": 1}, {"b": 2}]}
        result = resolve_node_variables(templates, state)
        assert result == {"items": [{"a": 1}, {"b": 2}]}

    @pytest.mark.req("REQ-YG-051")
    def test_missing_state_resolves_to_none(self):
        """Template referencing missing state resolves to None."""
        templates = {"missing": "{state.nonexistent}"}
        state = {"other": 1}
        result = resolve_node_variables(templates, state)
        assert result == {"missing": None}

    @pytest.mark.req("REQ-YG-051")
    def test_false_and_zero_not_filtered(self):
        """False and 0 are NOT filtered from state (only None is filtered)."""
        state = {"flag": False, "count": 0, "text": ""}
        result = resolve_node_variables(None, state)
        assert result["flag"] is False
        assert result["count"] == 0
        assert result["text"] == ""


# ──────────────────────────────────────────────────────────
# Section 11: Context Differences (resolve_state_expression vs resolve_template)
# ──────────────────────────────────────────────────────────


class TestContextDifferences:
    """Document the differences between the two expression resolution paths."""

    @pytest.mark.req("REQ-YG-051")
    def test_resolve_state_expression_strict_on_missing(self):
        """resolve_state_expression raises KeyError on missing path."""
        with pytest.raises(KeyError):
            resolve_state_expression("{missing}", {"a": 1})

    @pytest.mark.req("REQ-YG-051")
    def test_resolve_template_lenient_on_missing(self):
        """resolve_template returns None on missing path."""
        assert resolve_template("{state.missing}", {"a": 1}) is None

    @pytest.mark.req("REQ-YG-051")
    def test_resolve_state_expression_allows_no_prefix(self):
        """resolve_state_expression: {field} works (no state. prefix needed)."""
        assert resolve_state_expression("{name}", {"name": "Alice"}) == "Alice"

    @pytest.mark.req("REQ-YG-051")
    def test_resolve_template_requires_state_prefix(self):
        """resolve_template: {field} without state. returns as-is."""
        assert resolve_template("{name}", {"name": "Alice"}) == "{name}"

    @pytest.mark.req("REQ-YG-051")
    def test_resolve_template_handles_arithmetic(self):
        """resolve_template handles arithmetic; resolve_state_expression does not."""
        assert resolve_template("{state.x + 1}", {"x": 5}) == 6

    @pytest.mark.req("REQ-YG-051")
    def test_resolve_state_expression_no_arithmetic(self):
        """resolve_state_expression doesn't handle arithmetic — raises KeyError."""
        with pytest.raises(KeyError):
            resolve_state_expression("{state.x + 1}", {"x": 5})

    @pytest.mark.req("REQ-YG-051")
    def test_condition_uses_bare_paths(self):
        """evaluate_condition uses bare paths — no braces, no state. prefix."""
        assert evaluate_condition("score < 0.8", {"score": 0.5}) is True

    @pytest.mark.req("REQ-YG-051")
    def test_condition_right_side_resolves_state(self):
        """Condition right side resolves state ref before falling back to literal.

        Fixed in FR-024: unquoted identifiers on the right side now try state
        path resolution first, falling back to literal string if not found.
        """
        state = {"a": 5, "b": 10}
        # 'a < b' -> left=5, right=state["b"]=10 -> 5 < 10 -> True
        assert evaluate_condition("a < b", state) is True


# ──────────────────────────────────────────────────────────
# Section 12: _apply_operator edge cases
# ──────────────────────────────────────────────────────────


class TestApplyOperatorEdgeCases:
    """Verify _apply_operator behavior for documentation."""

    @pytest.mark.req("REQ-YG-051")
    def test_string_plus_string(self):
        """String + string concatenates."""
        assert _apply_operator("hello ", "+", "world") == "hello world"

    @pytest.mark.req("REQ-YG-051")
    def test_unknown_operator_raises(self):
        """Unknown operator raises ValueError."""
        with pytest.raises(ValueError, match="Unknown operator"):
            _apply_operator(1, "%", 2)

    @pytest.mark.req("REQ-YG-051")
    def test_int_plus_float(self):
        """int + float = float."""
        result = _apply_operator(5, "+", 0.5)
        assert result == 5.5
        assert isinstance(result, float)


# ──────────────────────────────────────────────────────────
# Section 13: Edge Cases & Gotchas (TDD-discovered)
# ──────────────────────────────────────────────────────────


class TestEdgeCasesAndGotchas:
    """Behaviors discovered through TDD — important for documentation."""

    @pytest.mark.req("REQ-YG-051")
    def test_state_key_named_state(self):
        """If state has a key named 'state', {state.state.x} works.

        After stripping 'state.' prefix, path 'state.x' → state['state']['x'].
        """
        state = {"state": {"x": "found"}}
        assert resolve_template("{state.state.x}", state) == "found"

    @pytest.mark.req("REQ-YG-051")
    def test_integer_dict_keys_not_supported(self):
        """Integer dict keys don't work — path segments are always strings.

        {state.items.0} tries dict.get('0') which fails for int key 0.
        """
        state = {"items": {0: "zero"}}
        assert resolve_template("{state.items.0}", state) is None

    @pytest.mark.req("REQ-YG-051")
    def test_condition_and_inside_quoted_value_works(self):
        """'and' inside a quoted string value is handled correctly.

        Fixed in FR-024: quote-aware split no longer breaks on
        'and'/'or' inside quoted strings.
        """
        result = evaluate_condition(
            "status == 'done and dusted'", {"status": "done and dusted"}
        )
        assert result is True  # Fixed: now evaluates correctly

    @pytest.mark.req("REQ-YG-051")
    def test_condition_or_inside_quoted_value_works(self):
        """'or' inside a quoted string value is handled correctly.

        Fixed in FR-024: quote-aware split no longer breaks on 'or' inside quotes.
        """
        result = evaluate_condition("status == 'yes or no'", {"status": "yes or no"})
        assert result is True  # Fixed: no longer raises

    @pytest.mark.req("REQ-YG-051")
    def test_string_true_not_equal_to_boolean_true(self):
        """String 'true' != boolean True in condition comparison.

        flag == true (no quotes) → right side parsed as boolean True
        flag == 'true' (quoted) → right side parsed as string 'true'
        """
        # Boolean True matches boolean true
        assert evaluate_condition("flag == true", {"flag": True}) is True
        # String 'true' matches quoted 'true'
        assert evaluate_condition("flag == 'true'", {"flag": "true"}) is True
        # String 'true' does NOT match unquoted true (boolean)
        assert evaluate_condition("flag == true", {"flag": "true"}) is False
        # Boolean True does NOT match quoted 'true' (string)
        assert evaluate_condition("flag == 'true'", {"flag": True}) is False

    @pytest.mark.req("REQ-YG-051")
    def test_condition_right_side_resolves_state_ref(self):
        """Right side of condition resolves state ref when available.

        Fixed in FR-024: 'a < b' → left=state['a'], right=state['b'].
        """
        state = {"a": 3, "b": 10}
        # 'b' is resolved as state path → state["b"] = 10
        # 3 < 10 → True
        assert evaluate_condition("a < b", state) is True

    @pytest.mark.req("REQ-YG-051")
    def test_resolve_state_expression_no_arithmetic(self):
        """resolve_state_expression does NOT handle arithmetic.

        '{state.x + 1}' strips 'state.' → path 'x + 1' → KeyError.
        """
        with pytest.raises(KeyError, match="x \\+ 1"):
            resolve_state_expression("{state.x + 1}", {"x": 5})

    @pytest.mark.req("REQ-YG-051")
    def test_falsy_values_are_real_values(self):
        """0, False, '', [] are all real resolved values, not 'missing'."""
        state = {"zero": 0, "false": False, "empty": "", "nil_list": []}
        assert resolve_state_path("zero", state) == 0
        assert resolve_state_path("false", state) is False
        assert resolve_state_path("empty", state) == ""
        assert resolve_state_path("nil_list", state) == []


# ──────────────────────────────────────────────────────────────────────
# FR-024 Expression Hardening (RED tests — must fail before implementation)
# ──────────────────────────────────────────────────────────────────────


class TestFR024Fix1QuoteAwareSplit:
    """Fix 1: 'and'/'or' inside quoted string values must NOT split."""

    @pytest.mark.req("REQ-YG-052")
    def test_condition_and_in_quoted_value_works(self):
        """'status == \"done and dusted\"' must evaluate to True."""
        result = evaluate_condition(
            "status == 'done and dusted'", {"status": "done and dusted"}
        )
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_condition_or_in_quoted_value_works(self):
        """'status == \"yes or no\"' must evaluate to True."""
        result = evaluate_condition("status == 'yes or no'", {"status": "yes or no"})
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_condition_and_in_double_quoted_value(self):
        """Double-quoted string with 'and' must not split."""
        result = evaluate_condition(
            'status == "done and dusted"', {"status": "done and dusted"}
        )
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_condition_or_in_double_quoted_value(self):
        """Double-quoted string with 'or' must not split."""
        result = evaluate_condition('status == "yes or no"', {"status": "yes or no"})
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_condition_multiple_and_in_quoted_value(self):
        """Multiple 'and' keywords in quoted value must not split."""
        result = evaluate_condition(
            "label == 'this and that and the other'",
            {"label": "this and that and the other"},
        )
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_real_compound_and_still_works(self):
        """Real compound AND outside quotes must still work."""
        result = evaluate_condition("a > 1 and b < 10", {"a": 5, "b": 3})
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_real_compound_or_still_works(self):
        """Real compound OR outside quotes must still work."""
        result = evaluate_condition("a > 100 or b < 10", {"a": 1, "b": 3})
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_quoted_and_with_real_compound(self):
        """Mixed: quoted 'and' value AND real compound 'and'."""
        result = evaluate_condition(
            "label == 'fish and chips' and score > 5",
            {"label": "fish and chips", "score": 10},
        )
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_quoted_or_with_real_compound(self):
        """Mixed: quoted 'or' value AND real compound 'or'."""
        result = evaluate_condition(
            "label == 'yes or no' or score > 100",
            {"label": "yes or no", "score": 1},
        )
        assert result is True

    @pytest.mark.req("REQ-YG-052")
    def test_not_equal_with_and_in_value(self):
        """Not-equal with 'and' in value works correctly."""
        result = evaluate_condition(
            "status != 'done and dusted'", {"status": "pending"}
        )
        assert result is True


class TestFR024Fix2StateRefOnRight:
    """Fix 2: Right side of condition can reference state values."""

    @pytest.mark.req("REQ-YG-053")
    def test_condition_state_ref_on_right(self):
        """'score < threshold' compares state.score to state.threshold."""
        state = {"score": 3, "threshold": 10}
        assert evaluate_condition("score < threshold", state) is True

    @pytest.mark.req("REQ-YG-053")
    def test_condition_state_ref_on_right_false(self):
        """'score < threshold' returns False when not satisfied."""
        state = {"score": 20, "threshold": 10}
        assert evaluate_condition("score < threshold", state) is False

    @pytest.mark.req("REQ-YG-053")
    def test_condition_state_ref_equality(self):
        """'a == b' compares two state values."""
        state = {"a": "hello", "b": "hello"}
        assert evaluate_condition("a == b", state) is True

    @pytest.mark.req("REQ-YG-053")
    def test_condition_state_ref_equality_different(self):
        """'a == b' returns False when state values differ."""
        state = {"a": "hello", "b": "world"}
        assert evaluate_condition("a == b", state) is False

    @pytest.mark.req("REQ-YG-053")
    def test_condition_right_literal_fallback(self):
        """When right side is not in state, fall back to literal string."""
        state = {"a": "hello"}
        # 'b' not in state → treat as literal string "hello" == "hello"
        # Actually, 'hello' is not 'b', so this should be False
        assert evaluate_condition("a == b", state) is False
        # But bare literal still works
        assert evaluate_condition("a == hello", state) is True

    @pytest.mark.req("REQ-YG-053")
    def test_condition_right_numeric_literal_still_works(self):
        """Numeric right side is still parsed as number, not state ref."""
        state = {"score": 5}
        assert evaluate_condition("score > 3", state) is True
        assert evaluate_condition("score < 10", state) is True

    @pytest.mark.req("REQ-YG-053")
    def test_condition_right_quoted_string_not_resolved(self):
        """Quoted right side is literal, not a state reference."""
        state = {"a": "threshold", "threshold": 999}
        # 'threshold' (quoted) should be literal string, not state lookup
        assert evaluate_condition("a == 'threshold'", state) is True

    @pytest.mark.req("REQ-YG-053")
    def test_condition_right_boolean_literal_still_works(self):
        """Boolean literals on right side still parsed correctly."""
        state = {"flag": True}
        assert evaluate_condition("flag == true", state) is True
        assert evaluate_condition("flag == false", state) is False

    @pytest.mark.req("REQ-YG-053")
    def test_condition_nested_state_ref_on_right(self):
        """Dotted path on right side resolves nested state."""
        state = {"score": 5, "config": {"threshold": 10}}
        assert evaluate_condition("score < config.threshold", state) is True

    @pytest.mark.req("REQ-YG-053")
    def test_condition_state_ref_both_sides_numeric(self):
        """Numeric comparison between two state values."""
        state = {"price": 25.0, "budget": 30.0}
        assert evaluate_condition("price <= budget", state) is True
        state2 = {"price": 35.0, "budget": 30.0}
        assert evaluate_condition("price <= budget", state2) is False


class TestFR024Fix3ChainedArithmetic:
    """Fix 3: Chained arithmetic expressions must raise ValueError."""

    @pytest.mark.req("REQ-YG-054")
    def test_chained_addition_raises(self):
        """'{state.a + state.b + state.c}' must raise ValueError."""
        state = {"a": 1, "b": 2, "c": 3}
        with pytest.raises(ValueError, match="[Cc]hained"):
            resolve_template("{state.a + state.b + state.c}", state)

    @pytest.mark.req("REQ-YG-054")
    def test_chained_mixed_ops_raises(self):
        """'{state.a + state.b - state.c}' must raise ValueError."""
        state = {"a": 10, "b": 5, "c": 3}
        with pytest.raises(ValueError, match="[Cc]hained"):
            resolve_template("{state.a + state.b - state.c}", state)

    @pytest.mark.req("REQ-YG-054")
    def test_chained_with_literals_raises(self):
        """'{state.a + 1 + 2}' must raise ValueError."""
        state = {"a": 10}
        with pytest.raises(ValueError, match="[Cc]hained"):
            resolve_template("{state.a + 1 + 2}", state)

    @pytest.mark.req("REQ-YG-054")
    def test_binary_arithmetic_still_works(self):
        """Normal binary arithmetic must continue working."""
        state = {"a": 10, "b": 5}
        assert resolve_template("{state.a + state.b}", state) == 15
        assert resolve_template("{state.a - state.b}", state) == 5
        assert resolve_template("{state.a * state.b}", state) == 50
        assert resolve_template("{state.a + 1}", state) == 11
