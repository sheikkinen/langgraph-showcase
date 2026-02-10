"""Python function loader for type: python nodes.

This module enables YAML graphs to call arbitrary Python functions
by specifying the module path and function name.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PythonToolConfig:
    """Configuration for a Python tool.

    Attributes:
        module: Full module path (e.g., "examples.storyboard.nodes.image_node")
        function: Function name within the module
        description: Human-readable description
    """

    module: str
    function: str
    description: str = ""


def load_python_function(config: PythonToolConfig) -> Callable:
    """Load a Python function from module path.

    Args:
        config: Python tool configuration

    Returns:
        The loaded function

    Raises:
        ImportError: If module cannot be imported
        AttributeError: If function not found in module
    """
    # Ensure current working directory is in path for project imports
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    try:
        module = importlib.import_module(config.module)
    except ImportError as e:
        logger.error(f"Failed to import module: {config.module}")
        raise ImportError(f"Cannot import module '{config.module}': {e}") from e

    try:
        func = getattr(module, config.function)
    except AttributeError as e:
        logger.error(f"Function not found: {config.function} in {config.module}")
        raise AttributeError(
            f"Function '{config.function}' not found in module '{config.module}'"
        ) from e

    if not callable(func):
        raise TypeError(f"'{config.function}' in '{config.module}' is not callable")

    logger.debug(f"Loaded Python function: {config.module}.{config.function}")
    return func


def parse_python_tools(tools_config: dict[str, Any]) -> dict[str, PythonToolConfig]:
    """Parse Python tools from YAML tools section.

    Only extracts tools with type: python.

    Args:
        tools_config: Dict from YAML tools: section

    Returns:
        Registry mapping tool names to PythonToolConfig objects
    """
    registry: dict[str, PythonToolConfig] = {}

    for name, config in tools_config.items():
        if config.get("type") != "python":
            continue

        if "module" not in config or "function" not in config:
            logger.warning(
                f"Python tool '{name}' missing 'module' or 'function', skipping"
            )
            continue

        registry[name] = PythonToolConfig(
            module=config["module"],
            function=config["function"],
            description=config.get("description", ""),
        )

    return registry


def create_python_node(
    node_name: str,
    node_config: dict[str, Any],
    python_tools: dict[str, PythonToolConfig],
) -> Callable[[dict[str, Any]], dict]:
    """Create a node that executes a Python function.

    The function receives the full state dict and should return
    a partial state update dict.

    Args:
        node_name: Name of the node in the graph
        node_config: Node configuration from YAML
        python_tools: Registry of available Python tools

    Returns:
        Node function that executes the Python function
    """
    tool_name = node_config.get("tool") or node_config.get("function")
    if not tool_name:
        raise ValueError(f"Python node '{node_name}' must specify 'tool' or 'function'")

    if tool_name not in python_tools:
        raise KeyError(f"Python tool '{tool_name}' not found in tools registry")

    tool_config = python_tools[tool_name]
    state_key = node_config.get("state_key", node_name)
    on_error = node_config.get("on_error", "fail")
    loop_limit = node_config.get("loop_limit")

    # Load the function at node creation time
    func = load_python_function(tool_config)

    def node_fn(state: dict[str, Any]) -> dict:
        """Execute the Python function and return state update."""
        # FR-027: Check loop limit (same pattern as LLM nodes)
        from yamlgraph.error_handlers import check_loop_limit

        loop_counts = dict(state.get("_loop_counts") or {})
        current_count = loop_counts.get(node_name, 0)

        if check_loop_limit(node_name, loop_limit, current_count):
            return {"_loop_limit_reached": True, "current_step": node_name}

        loop_counts[node_name] = current_count + 1

        logger.info(f"🐍 Executing Python node: {node_name} -> {tool_name}")

        try:
            result = func(state)

            # If function returns a dict, merge with node metadata
            if isinstance(result, dict):
                result["current_step"] = node_name
                result["_loop_counts"] = loop_counts
                return result
            else:
                # Function returned a single value, store in state_key
                return {
                    state_key: result,
                    "current_step": node_name,
                    "_loop_counts": loop_counts,
                }

        except Exception as e:
            logger.error(f"Python node {node_name} failed: {e}")

            if on_error == "skip":
                from yamlgraph.error_handlers import build_skip_error_state

                return build_skip_error_state(
                    node_name=node_name,
                    state_key=state_key,
                    error_message=str(e),
                    state=state,
                )
            else:
                raise

    node_fn.__name__ = f"{node_name}_python_node"
    return node_fn
