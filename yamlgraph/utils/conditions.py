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
from yamlgraph.utils.parsing import parse_literal

# Regex patterns for expression parsing
# Valid operators: <=, >=, ==, !=, <, > (strict matching)
COMPARISON_PATTERN = re.compile(
    r"^\s*([a-zA-Z_][\w.]*)\s*(<=|>=|==|!=|<(?!<)|>(?!>))\s*(.+?)\s*$"
)
COMPOUND_AND_PATTERN = re.compile(r"\s+and\s+", re.IGNORECASE)
COMPOUND_OR_PATTERN = re.compile(r"\s+or\s+", re.IGNORECASE)


def _split_compound(expr: str, keyword: str) -> list[str] | None:
    """Split on ' and ' / ' or ' only outside quoted strings.

    Args:
        expr: Condition expression string
        keyword: 'and' or 'or' (case-insensitive)

    Returns:
        List of parts if split occurred, None if keyword not found outside quotes
    """
    parts: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    i = 0
    pattern = f" {keyword} "
    pat_len = len(pattern)

    while i < len(expr):
        ch = expr[i]
        if ch in ("'", '"') and in_quote is None:
            in_quote = ch
        elif ch == in_quote:
            in_quote = None

        if in_quote is None and expr[i : i + pat_len].lower() == pattern:
            parts.append("".join(current))
            current = []
            i += pat_len
            continue

        current.append(ch)
        i += 1

    parts.append("".join(current))
    return parts if len(parts) > 1 else None


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


def _resolve_right_value(right_str: str, state: dict[str, Any]) -> Any:
    """Resolve right side of comparison: literal first, then state path.

    Priority order:
    1. Quoted strings → literal (never state ref)
    2. Boolean/null keywords → literal
    3. Numeric values → literal
    4. Unquoted identifier → try state path, fall back to literal string

    Args:
        right_str: Raw right-side string from comparison
        state: State dictionary

    Returns:
        Resolved value
    """
    right_str = right_str.strip()

    # Quoted strings are always literal
    if (right_str.startswith("'") and right_str.endswith("'")) or (
        right_str.startswith('"') and right_str.endswith('"')
    ):
        return parse_literal(right_str)

    # Boolean/null keywords are always literal
    if right_str.lower() in ("true", "false", "null", "none"):
        return parse_literal(right_str)

    # Numeric values are always literal
    try:
        parsed = parse_literal(right_str)
        if isinstance(parsed, int | float):
            return parsed
    except (ValueError, TypeError):
        pass

    # Unquoted identifier: try state path first
    val = resolve_state_path(right_str, state)
    if val is not None:
        return val

    # Fallback: return as literal string
    return right_str


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
    right_value = _resolve_right_value(right_str, state)

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

    # Handle compound OR (lower precedence) — quote-aware split
    or_parts = _split_compound(expr, "or")
    if or_parts is not None:
        return any(evaluate_condition(part, state) for part in or_parts)

    # Handle compound AND — quote-aware split
    and_parts = _split_compound(expr, "and")
    if and_parts is not None:
        return all(evaluate_condition(part, state) for part in and_parts)

    # Parse single comparison
    match = COMPARISON_PATTERN.match(expr)
    if not match:
        raise ValueError(f"Invalid condition expression: {expr}")

    left_path, operator, right_str = match.groups()
    return evaluate_comparison(left_path, operator, right_str, state)
