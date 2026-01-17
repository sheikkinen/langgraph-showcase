"""Unit tests for conditions and routing modules.

Tests the expression evaluation and routing functions used for
graph edge conditions.

Note: resolve_value tests are in test_expressions.py (TestResolveStatePath)
since resolve_value delegates to resolve_state_path.
"""

import pytest
from pydantic import BaseModel

from showcase.routing import make_expr_router_fn, make_router_fn
from showcase.utils.conditions import (
    evaluate_comparison,
    evaluate_condition,
    parse_literal,
)


class TestParseLiteral:
    """Tests for parse_literal function."""

    def test_integer(self):
        """Should parse integer."""
        assert parse_literal("42") == 42
        assert parse_literal("-5") == -5

    def test_float(self):
        """Should parse float."""
        assert parse_literal("0.8") == 0.8
        assert parse_literal("-3.14") == -3.14

    def test_boolean_true(self):
        """Should parse boolean true (case insensitive)."""
        assert parse_literal("true") is True
        assert parse_literal("True") is True
        assert parse_literal("TRUE") is True

    def test_boolean_false(self):
        """Should parse boolean false."""
        assert parse_literal("false") is False
        assert parse_literal("False") is False

    def test_null_none(self):
        """Should parse null/none."""
        assert parse_literal("null") is None
        assert parse_literal("None") is None

    def test_quoted_string(self):
        """Should parse quoted strings."""
        assert parse_literal('"hello"') == "hello"
        assert parse_literal("'world'") == "world"

    def test_unquoted_string(self):
        """Should return unquoted string as-is."""
        assert parse_literal("hello") == "hello"


class TestEvaluateComparison:
    """Tests for evaluate_comparison function."""

    def test_less_than(self):
        """Should evaluate < operator."""
        state = {"score": 0.5}
        assert evaluate_comparison("score", "<", "0.8", state) is True
        assert evaluate_comparison("score", "<", "0.3", state) is False

    def test_greater_than(self):
        """Should evaluate > operator."""
        state = {"score": 0.9}
        assert evaluate_comparison("score", ">", "0.5", state) is True
        assert evaluate_comparison("score", ">", "1.0", state) is False

    def test_less_than_or_equal(self):
        """Should evaluate <= operator."""
        state = {"value": 5}
        assert evaluate_comparison("value", "<=", "5", state) is True
        assert evaluate_comparison("value", "<=", "10", state) is True
        assert evaluate_comparison("value", "<=", "3", state) is False

    def test_greater_than_or_equal(self):
        """Should evaluate >= operator."""
        state = {"value": 5}
        assert evaluate_comparison("value", ">=", "5", state) is True
        assert evaluate_comparison("value", ">=", "3", state) is True
        assert evaluate_comparison("value", ">=", "10", state) is False

    def test_equal(self):
        """Should evaluate == operator."""
        state = {"status": "done", "count": 3}
        assert evaluate_comparison("status", "==", '"done"', state) is True
        assert evaluate_comparison("count", "==", "3", state) is True
        assert evaluate_comparison("status", "==", '"pending"', state) is False

    def test_not_equal(self):
        """Should evaluate != operator."""
        state = {"status": "done"}
        assert evaluate_comparison("status", "!=", '"pending"', state) is True
        assert evaluate_comparison("status", "!=", '"done"', state) is False

    def test_missing_value_returns_false(self):
        """Missing value should return False for comparison (except ==, !=)."""
        state = {"a": 1}
        assert evaluate_comparison("missing", "<", "5", state) is False
        assert evaluate_comparison("missing", ">", "5", state) is False

    def test_missing_value_equals_none(self):
        """Missing value equals None."""
        state = {"a": 1}
        assert evaluate_comparison("missing", "==", "None", state) is True

    def test_type_mismatch_returns_false(self):
        """Type mismatch in comparison should return False."""
        state = {"value": "not_a_number"}
        assert evaluate_comparison("value", "<", "5", state) is False


class TestEvaluateCondition:
    """Tests for evaluate_condition function."""

    def test_simple_comparison(self):
        """Should evaluate simple comparison."""
        assert evaluate_condition("score < 0.8", {"score": 0.5}) is True
        assert evaluate_condition("score >= 0.8", {"score": 0.9}) is True

    def test_nested_path(self):
        """Should evaluate nested path comparison."""
        state = {"critique": {"score": 0.7}}
        assert evaluate_condition("critique.score < 0.8", state) is True
        assert evaluate_condition("critique.score >= 0.8", state) is False

    def test_compound_and(self):
        """Should evaluate AND expression."""
        state = {"a": 5, "b": 10}
        assert evaluate_condition("a > 1 and b < 20", state) is True
        assert evaluate_condition("a > 1 and b > 20", state) is False
        assert evaluate_condition("a > 10 and b < 20", state) is False

    def test_compound_or(self):
        """Should evaluate OR expression."""
        state = {"a": 5, "b": 10}
        assert evaluate_condition("a > 10 or b < 20", state) is True
        assert evaluate_condition("a > 1 or b > 100", state) is True
        assert evaluate_condition("a > 10 or b > 100", state) is False

    def test_mixed_and_or(self):
        """Should handle mixed AND/OR (AND has higher precedence)."""
        state = {"a": 5, "b": 10, "c": 15}
        # a > 10 OR (b < 20 AND c > 10) -> False OR True -> True
        assert evaluate_condition("a > 10 or b < 20 and c > 10", state) is True

    def test_whitespace_handling(self):
        """Should handle various whitespace."""
        state = {"score": 0.5}
        assert evaluate_condition("  score   <   0.8  ", state) is True
        assert evaluate_condition("score<0.8", state) is True

    def test_invalid_expression_raises(self):
        """Should raise ValueError for invalid expression."""
        with pytest.raises(ValueError, match="Invalid condition"):
            evaluate_condition("not a valid expression !!!", {})

    def test_pydantic_model_in_state(self):
        """Should work with Pydantic models in state."""

        class Critique(BaseModel):
            score: float

        state = {"critique": Critique(score=0.75)}
        assert evaluate_condition("critique.score < 0.8", state) is True
        assert evaluate_condition("critique.score >= 0.8", state) is False


class TestMakeRouterFn:
    """Tests for make_router_fn factory."""

    def test_routes_to_matching_target(self):
        """Should route to target matching _route."""
        router = make_router_fn(["positive", "negative", "neutral"])
        assert router({"_route": "positive"}) == "positive"
        assert router({"_route": "negative"}) == "negative"

    def test_defaults_to_first_target(self):
        """Should default to first target when no match."""
        router = make_router_fn(["a", "b", "c"])
        assert router({"_route": "unknown"}) == "a"
        assert router({}) == "a"

    def test_ignores_invalid_route(self):
        """Should ignore route not in targets."""
        router = make_router_fn(["x", "y"])
        assert router({"_route": "z"}) == "x"


class TestMakeExprRouterFn:
    """Tests for make_expr_router_fn factory."""

    def test_routes_on_first_matching_condition(self):
        """Should route to first matching condition."""
        edges = [
            ("score < 0.5", "refine"),
            ("score >= 0.5", "done"),
        ]
        router = make_expr_router_fn(edges, "test_node")

        assert router({"score": 0.3}) == "refine"
        assert router({"score": 0.8}) == "done"

    def test_loop_limit_takes_precedence(self):
        """Should return END when loop limit reached."""
        from langgraph.graph import END

        edges = [("score < 0.8", "continue")]
        router = make_expr_router_fn(edges, "test_node")

        assert router({"_loop_limit_reached": True, "score": 0.5}) == END

    def test_defaults_to_end_when_no_match(self):
        """Should return END when no condition matches."""
        from langgraph.graph import END

        edges = [
            ("score < 0.5", "a"),
            ("score > 0.9", "b"),
        ]
        router = make_expr_router_fn(edges, "test_node")

        # score = 0.7 doesn't match either
        assert router({"score": 0.7}) == END

    def test_handles_condition_error_gracefully(self):
        """Should log warning and continue on condition error."""

        edges = [
            ("invalid!!! expression", "a"),  # This will fail
            ("score >= 0.8", "done"),
        ]
        router = make_expr_router_fn(edges, "test_node")

        # Should skip invalid and match second condition
        assert router({"score": 0.9}) == "done"

    def test_condition_order_matters(self):
        """First matching condition wins."""
        edges = [
            ("score >= 0.5", "half"),
            ("score >= 0.8", "high"),  # Never reached if first matches
        ]
        router = make_expr_router_fn(edges, "test_node")

        # Both conditions true, but first wins
        assert router({"score": 0.9}) == "half"
