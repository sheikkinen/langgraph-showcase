"""Routing utilities for LangGraph edge conditions.

Provides factory functions for creating router functions that determine
which node to route to based on state values and expressions.
"""

import logging
import warnings
from collections.abc import Callable
from typing import Any

from langgraph.graph import END

from showcase.utils.conditions import evaluate_condition

# Type alias for dynamic state
GraphState = dict[str, Any]

logger = logging.getLogger(__name__)


def should_continue(state: GraphState) -> str:
    """Default routing condition: continue or end.

    .. deprecated:: 1.0
        Use expression-based routing with `make_expr_router_fn` instead.
        Will be removed in v2.0.

    Args:
        state: Current pipeline state

    Returns:
        'continue' if should proceed, 'end' if should stop
    """
    warnings.warn(
        "should_continue is deprecated. Use expression-based routing instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    if state.get("error") is not None:
        return "end"
    if state.get("generated") is None:
        return "end"
    return "continue"


def make_router_fn(targets: list[str]) -> Callable[[dict], str]:
    """Create a router function that reads _route from state.

    Used for type: router nodes with conditional edges to multiple targets.

    NOTE: Use `state: dict` not `state: GraphState` - type hints cause
    LangGraph to filter state fields. See docs/debug-router-type-hints.md

    Args:
        targets: List of valid target node names

    Returns:
        Router function that returns the target node name
    """

    def router_fn(state: dict) -> str:
        route = state.get("_route")
        logger.debug(f"Router: _route={route}, targets={targets}")
        if route and route in targets:
            logger.debug(f"Router: matched route {route}")
            return route
        # Default to first target
        logger.debug(f"Router: defaulting to {targets[0]}")
        return targets[0]

    return router_fn


def make_expr_router_fn(
    edges: list[tuple[str, str]],
    source_node: str,
) -> Callable[[GraphState], str]:
    """Create router that evaluates expression conditions.

    Used for reflexion-style loops with expression-based conditions
    like "critique.score < 0.8".

    Args:
        edges: List of (condition, target) tuples
        source_node: Name of the source node (for logging)

    Returns:
        Router function that evaluates conditions and returns target
    """

    def expr_router_fn(state: GraphState) -> str:
        # Check loop limit first
        if state.get("_loop_limit_reached"):
            return END

        for condition, target in edges:
            try:
                if evaluate_condition(condition, state):
                    logger.debug(
                        f"Condition '{condition}' matched, routing to {target}"
                    )
                    return target
            except ValueError as e:
                logger.warning(f"Failed to evaluate condition '{condition}': {e}")
        # No condition matched - this shouldn't happen with well-formed graphs
        logger.warning(f"No condition matched for {source_node}, defaulting to END")
        return END

    return expr_router_fn


__all__ = ["should_continue", "make_router_fn", "make_expr_router_fn"]
