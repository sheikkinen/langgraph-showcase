"""Expression resolution utilities for YAML graphs.

Consolidated module for all state path/expression resolution.
Use these functions instead of duplicating resolution logic elsewhere.
"""

from typing import Any


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


def resolve_template(template: str | Any, state: dict[str, Any]) -> Any:
    """Resolve a {state.field} template to its value.

    Unlike resolve_state_expression, returns None instead of raising
    when path not found. Used for optional variable resolution.

    Args:
        template: Template string like "{state.field}" or "{state.obj.attr}"
        state: Current pipeline state

    Returns:
        Resolved value or None if not found
    """
    STATE_PREFIX = "{state."
    STATE_SUFFIX = "}"

    if not isinstance(template, str):
        return template

    if not (template.startswith(STATE_PREFIX) and template.endswith(STATE_SUFFIX)):
        return template

    # Extract path: "{state.foo.bar}" -> "foo.bar"
    path = template[len(STATE_PREFIX) : -len(STATE_SUFFIX)]
    return resolve_state_path(path, state)
