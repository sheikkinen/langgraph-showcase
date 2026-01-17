"""Condition expression evaluation for graph routing.

Provides safe evaluation of condition expressions without using eval().
Supports comparisons and compound boolean expressions.

Examples:
    >>> evaluate_condition("score < 0.8", {"score": 0.5})
    True
    >>> evaluate_condition("a > 1 and b < 2", {"a": 2, "b": 1})
    True
"""

import re
from typing import Any

from yamlgraph.utils.expressions import resolve_state_path

# Regex patterns for expression parsing
# Valid operators: <=, >=, ==, !=, <, > (strict matching)
COMPARISON_PATTERN = re.compile(
    r"^\s*([a-zA-Z_][\w.]*)\s*(<=|>=|==|!=|<(?!<)|>(?!>))\s*(.+?)\s*$"
)
COMPOUND_AND_PATTERN = re.compile(r"\s+and\s+", re.IGNORECASE)
COMPOUND_OR_PATTERN = re.compile(r"\s+or\s+", re.IGNORECASE)


def resolve_value(path: str, state: dict) -> Any:
    """Resolve a dotted path to a value from state.

    Delegates to consolidated resolve_state_path in expressions module.

    Args:
        path: Dotted path like "critique.score"
        state: State dictionary

    Returns:
        Resolved value or None if not found
    """
    return resolve_state_path(path, state)


def parse_literal(value_str: str) -> Any:
    """Parse a literal value from expression.

    Args:
        value_str: String representation of value

    Returns:
        Parsed Python value
    """
    value_str = value_str.strip()

    # Handle quoted strings
    if (value_str.startswith('"') and value_str.endswith('"')) or (
        value_str.startswith("'") and value_str.endswith("'")
    ):
        return value_str[1:-1]

    # Handle special keywords
    if value_str.lower() == "true":
        return True
    if value_str.lower() == "false":
        return False
    if value_str.lower() == "null" or value_str.lower() == "none":
        return None

    # Handle numbers
    try:
        if "." in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        # Return as string if not a number
        return value_str


def evaluate_comparison(
    left_path: str, operator: str, right_str: str, state: dict[str, Any]
) -> bool:
    """Evaluate a single comparison expression.

    Args:
        left_path: Dotted path to left value
        operator: Comparison operator
        right_str: String representation of right value
        state: State dictionary

    Returns:
        Boolean result of comparison
    """
    left_value = resolve_value(left_path, state)
    right_value = parse_literal(right_str)

    # Handle missing left value
    if left_value is None and operator not in ("==", "!="):
        return False

    try:
        if operator == "<":
            return left_value < right_value
        elif operator == ">":
            return left_value > right_value
        elif operator == "<=":
            return left_value <= right_value
        elif operator == ">=":
            return left_value >= right_value
        elif operator == "==":
            return left_value == right_value
        elif operator == "!=":
            return left_value != right_value
        else:
            raise ValueError(f"Unknown operator: {operator}")
    except TypeError:
        # Comparison failed (e.g., comparing None with number)
        return False


def evaluate_condition(expr: str, state: dict) -> bool:
    """Safely evaluate a condition expression against state.

    Uses pattern matching - no eval() for security.

    Args:
        expr: Condition expression like "score < 0.8" or "a > 1 and b < 2"
        state: State dictionary to evaluate against

    Returns:
        Boolean result of evaluation

    Raises:
        ValueError: If expression is malformed

    Examples:
        >>> evaluate_condition("score < 0.8", {"score": 0.5})
        True
        >>> evaluate_condition("critique.score >= 0.8", {"critique": obj})
        True
    """
    expr = expr.strip()

    # Handle compound OR (lower precedence)
    if COMPOUND_OR_PATTERN.search(expr):
        parts = COMPOUND_OR_PATTERN.split(expr)
        return any(evaluate_condition(part, state) for part in parts)

    # Handle compound AND
    if COMPOUND_AND_PATTERN.search(expr):
        parts = COMPOUND_AND_PATTERN.split(expr)
        return all(evaluate_condition(part, state) for part in parts)

    # Parse single comparison
    match = COMPARISON_PATTERN.match(expr)
    if not match:
        raise ValueError(f"Invalid condition expression: {expr}")

    left_path, operator, right_str = match.groups()
    return evaluate_comparison(left_path, operator, right_str, state)
