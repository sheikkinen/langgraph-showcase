"""Node factories for tool and agent nodes.

This module provides functions to create graph nodes that execute
shell tools, either deterministically (tool nodes) or via LLM
decision-making (agent nodes).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from yamlgraph.error_handlers import build_skip_error_state, check_loop_limit
from yamlgraph.tools.shell import ShellToolConfig, execute_shell_tool
from yamlgraph.utils.expressions import resolve_template

# Type alias for state - dynamic TypedDict at runtime
GraphState = dict[str, Any]

logger = logging.getLogger(__name__)


def resolve_state_variable(template: str, state: dict[str, Any]) -> str:
    """Resolve {state.path.to.value} to actual state value.

    Note: Uses consolidated resolve_template from expressions module.

    Args:
        template: String with {state.key} or {state.nested.key} placeholders
        state: Current graph state

    Returns:
        Resolved value (preserves type: lists, dicts, etc.)
    """
    value = resolve_template(template, state)
    # resolve_template returns the template unchanged if not a state expression
    if value is template:
        return template
    # Preserve the original type - don't convert to string
    # This allows lists and dicts to be passed to Jinja2 templates correctly
    return value


def resolve_variables(
    variables_config: dict[str, str],
    state: dict[str, Any],
) -> dict[str, Any]:
    """Resolve all variable templates against state.

    Args:
        variables_config: Dict of {var_name: template_string}
        state: Current graph state

    Returns:
        Dict of {var_name: resolved_value}
    """
    resolved = {}
    for key, template in variables_config.items():
        resolved[key] = resolve_state_variable(template, state)
    return resolved


def create_tool_node(
    node_name: str,
    node_config: dict[str, Any],
    tools: dict[str, ShellToolConfig],
) -> Callable[[GraphState], dict]:
    """Create a node that executes a shell tool.

    Args:
        node_name: Name of the node in the graph
        node_config: Node configuration from YAML
        tools: Registry of available tools

    Returns:
        Node function that executes the tool

    Raises:
        KeyError: If tool name not in registry
    """
    tool_name = node_config["tool"]
    tool_config = tools[tool_name]  # Raise KeyError if not found
    state_key = node_config.get("state_key", node_name)
    on_error = node_config.get("on_error", "fail")
    variables_template = node_config.get("variables", {})
    loop_limit = node_config.get("loop_limit")

    def node_fn(state: GraphState) -> dict:
        """Execute the shell tool and return state update."""
        # FR-027: Check loop limit (same pattern as LLM nodes)
        loop_counts = dict(state.get("_loop_counts") or {})
        current_count = loop_counts.get(node_name, 0)

        if check_loop_limit(node_name, loop_limit, current_count):
            return {"_loop_limit_reached": True, "current_step": node_name}

        loop_counts[node_name] = current_count + 1

        # Resolve variables from state
        variables = resolve_variables(variables_template, state)

        logger.info(f"🔧 Executing tool: {tool_name}")
        result = execute_shell_tool(tool_config, variables)

        if not result.success:
            logger.warning(f"Tool {tool_name} failed: {result.error}")

            if on_error == "skip":
                # Return with error tracked but don't raise
                return build_skip_error_state(
                    node_name=node_name,
                    state_key=state_key,
                    error_message=result.error or "Tool execution failed",
                    state=state,
                )
            else:
                # on_error == "fail" - raise exception
                raise RuntimeError(
                    f"Tool '{tool_name}' failed in node '{node_name}': {result.error}"
                )

        logger.info(f"✓ Tool {tool_name} completed")
        return {
            state_key: result.output,
            "current_step": node_name,
            "_loop_counts": loop_counts,
        }

    return node_fn
