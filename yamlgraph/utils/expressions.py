"""Expression resolution utilities for YAML graphs.

Consolidated module for all state path/expression resolution.
Use these functions instead of duplicating resolution logic elsewhere.
"""

import re
from typing import Any

# Pattern for arithmetic expressions: {state.field + 1} or {state.a + state.b}
ARITHMETIC_PATTERN = re.compile(r"^\{(state\.[a-zA-Z_][\w.]*)\s*([+\-*/])\s*(.+)\}$")

# Pattern to detect chained operations in the right operand
_CHAINED_OP_PATTERN = re.compile(
    r"(?:state\.[a-zA-Z_][\w.]*|[0-9]+(?:\.[0-9]+)?)\s*[+\-*/]\s*"
)


def resolve_state_path(path: str, state: dict[str, Any]) -> Any:
    """Resolve a dotted path to a value from state.

    Core resolution function - handles nested dict access and object attributes.
    This is the single source of truth for path resolution.

    Args:
        path: Dotted path like "critique.score" or "story.panels"
        state: State dictionary

    Returns:
        Resolved value or None if not found
    """
    if not path:
        return None

    parts = path.split(".")
    value = state

    for part in parts:
        if value is None:
            return None
        if isinstance(value, dict):
            value = value.get(part)
        else:
            # Try attribute access for objects (Pydantic models, etc.)
            value = getattr(value, part, None)

    return value


def resolve_state_expression(expr: str | Any, state: dict[str, Any]) -> Any:
    """Resolve {state.path.to.value} expressions.

    Supports expressions like:
        - "{name}" -> state["name"]
        - "{state.story.panels}" -> state["story"]["panels"]
        - "{story.title}" -> state["story"]["title"]

    Non-expression values (no braces) pass through unchanged.

    Args:
        expr: Expression string like "{state.story.panels}" or any value
        state: Current graph state dict

    Returns:
        Resolved value from state, or original value if not an expression

    Raises:
        KeyError: If path cannot be resolved in state
    """
    if not isinstance(expr, str):
        return expr

    if not (expr.startswith("{") and expr.endswith("}")):
        return expr

    path = expr[1:-1]  # Remove braces

    # Handle "state." prefix (optional)
    if path.startswith("state."):
        path = path[6:]  # Remove "state."

    # Navigate nested path
    value = state
    for key in path.split("."):
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif hasattr(value, key):
            # Support object attribute access (Pydantic models, etc.)
            value = getattr(value, key)
        else:
            raise KeyError(f"Cannot resolve '{key}' in path '{expr}'")

    return value


def _parse_operand(operand_str: str, state: dict[str, Any]) -> Any:
    """Parse an operand - either a state reference or a literal.

    Args:
        operand_str: String like "state.counter", "1", "[state.item]", etc.
        state: Current pipeline state

    Returns:
        Resolved value
    """
    operand_str = operand_str.strip()

    # State reference: state.field
    if operand_str.startswith("state."):
        path = operand_str[6:]  # Remove "state."
        return resolve_state_path(path, state)

    # List literal with state reference: [state.item]
    if operand_str.startswith("[") and operand_str.endswith("]"):
        inner = operand_str[1:-1].strip()
        if inner.startswith("state."):
            item = resolve_state_path(inner[6:], state)
            return [item]
        # Try to parse as literal
        return [_parse_literal(inner)]

    # Dict literal: {'key': state.value}
    if operand_str.startswith("{") and operand_str.endswith("}"):
        # Simple dict parsing - limited support
        inner = operand_str[1:-1].strip()
        result = {}
        # Parse simple key-value pairs
        for pair in inner.split(","):
            if ":" not in pair:
                continue
            key_part, val_part = pair.split(":", 1)
            key = key_part.strip().strip("'\"")
            val = val_part.strip()
            if val.startswith("state."):
                result[key] = resolve_state_path(val[6:], state)
            else:
                result[key] = _parse_literal(val)
        return result

    # Literal value
    return _parse_literal(operand_str)


# Import shared parsing utility (aliased to preserve internal name)
from yamlgraph.utils.parsing import parse_literal as _parse_literal  # noqa: E402


def _apply_operator(left: Any, operator: str, right: Any) -> Any:
    """Apply an arithmetic operator.

    Args:
        left: Left operand
        operator: One of +, -, *, /
        right: Right operand

    Returns:
        Result of operation
    """
    if operator == "+":
        # List concatenation or addition
        if isinstance(left, list):
            if isinstance(right, list):
                return left + right
            return left + [right]
        return left + right
    elif operator == "-":
        return left - right
    elif operator == "*":
        return left * right
    elif operator == "/":
        return left / right
    else:
        raise ValueError(f"Unknown operator: {operator}")


def resolve_template(template: str | Any, state: dict[str, Any]) -> Any:
    """Resolve a {state.field} template to its value.

    Supports:
    - Simple paths: {state.field}
    - Arithmetic: {state.counter + 1}
    - List operations: {state.history + [state.item]}

    Args:
        template: Template string like "{state.field}" or "{state.a + 1}"
        state: Current pipeline state

    Returns:
        Resolved value or None if not found
    """
    if not isinstance(template, str):
        return template

    if not (template.startswith("{") and template.endswith("}")):
        return template

    # Check for arithmetic expression first
    match = ARITHMETIC_PATTERN.match(template)
    if match:
        left_ref = match.group(1)  # e.g., "state.counter"
        operator = match.group(2)  # e.g., "+"
        right_str = match.group(3)  # e.g., "1" or "state.other"

        # Detect chained operations: {state.a + state.b + state.c}
        # The right_str would be "state.b + state.c" — contains another op
        if _CHAINED_OP_PATTERN.search(right_str):
            raise ValueError(
                f"Chained arithmetic not supported: {template}. "
                "Use intermediate state variables instead."
            )

        left = _parse_operand(left_ref, state)
        right = _parse_operand(right_str, state)

        if left is None:
            return None

        return _apply_operator(left, operator, right)

    # Simple state path
    STATE_PREFIX = "{state."
    if template.startswith(STATE_PREFIX) and template.endswith("}"):
        path = template[len(STATE_PREFIX) : -1]
        return resolve_state_path(path, state)

    return template


def resolve_node_variables(
    variable_templates: dict[str, str] | None,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Resolve node variables from templates or state.

    Shared utility for LLM nodes and streaming nodes.

    When templates are provided, resolves each template against state.
    When templates are empty/None, returns filtered state (no _ keys, no None values).

    Args:
        variable_templates: Dict of {var_name: template_string} or None
        state: Current graph state

    Returns:
        Dict of resolved variables for prompt execution
    """
    if variable_templates:
        variables = {}
        for key, template in variable_templates.items():
            resolved = resolve_template(template, state)
            # Preserve original types (lists, dicts) for Jinja2 templates
            variables[key] = resolved
        return variables

    # No explicit variable mapping - pass state as variables
    # Filter out internal keys and None values
    return {k: v for k, v in state.items() if not k.startswith("_") and v is not None}
