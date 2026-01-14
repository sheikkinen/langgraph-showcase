"""Node factories for tool and agent nodes.

This module provides functions to create graph nodes that execute
shell tools, either deterministically (tool nodes) or via LLM
decision-making (agent nodes).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

from showcase.models.schemas import ErrorType, PipelineError
from showcase.models.state import ShowcaseState
from showcase.tools.shell import ShellToolConfig, execute_shell_tool

logger = logging.getLogger(__name__)


def resolve_state_variable(template: str, state: dict[str, Any]) -> str:
    """Resolve {state.path.to.value} to actual state value.

    Args:
        template: String with {state.key} or {state.nested.key} placeholders
        state: Current graph state

    Returns:
        Resolved string value
    """
    if not template.startswith("{state."):
        return template

    # Extract the path: {state.foo.bar} -> foo.bar
    match = re.match(r"\{state\.([^}]+)\}", template)
    if not match:
        return template

    path = match.group(1)
    parts = path.split(".")

    value = state
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return template  # Can't resolve further

    return str(value) if value is not None else ""


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
) -> Callable[[ShowcaseState], dict]:
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

    def node_fn(state: ShowcaseState) -> dict:
        """Execute the shell tool and return state update."""
        # Resolve variables from state
        variables = resolve_variables(variables_template, state)

        logger.info(f"🔧 Executing tool: {tool_name}")
        result = execute_shell_tool(tool_config, variables)

        if not result.success:
            logger.warning(f"Tool {tool_name} failed: {result.error}")

            if on_error == "skip":
                # Return with error tracked but don't raise
                errors = list(state.get("errors") or [])
                errors.append(
                    PipelineError(
                        node=node_name,
                        type=ErrorType.UNKNOWN_ERROR,
                        message=result.error or "Tool execution failed",
                    )
                )
                return {
                    state_key: None,
                    "current_step": node_name,
                    "errors": errors,
                }
            else:
                # on_error == "fail" - raise exception
                raise RuntimeError(
                    f"Tool '{tool_name}' failed in node '{node_name}': {result.error}"
                )

        logger.info(f"✓ Tool {tool_name} completed")
        return {
            state_key: result.output,
            "current_step": node_name,
        }

    return node_fn
