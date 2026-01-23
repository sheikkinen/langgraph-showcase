"""Node Compiler - Compile YAML node configs to LangGraph nodes.

Extracted from graph_loader.py to keep modules under 400 lines.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langgraph.graph import StateGraph

from yamlgraph.constants import NodeType
from yamlgraph.map_compiler import compile_map_node
from yamlgraph.node_factory import (
    create_interrupt_node,
    create_node_function,
    create_passthrough_node,
    create_subgraph_node,
    create_tool_call_node,
)
from yamlgraph.tools.agent import create_agent_node
from yamlgraph.tools.nodes import create_tool_node
from yamlgraph.tools.python_tool import create_python_node

if TYPE_CHECKING:
    from yamlgraph.graph_loader import GraphConfig

logger = logging.getLogger(__name__)


def compile_node(
    node_name: str,
    node_config: dict[str, Any],
    graph: StateGraph,
    config: "GraphConfig",
    tools: dict[str, Any],
    python_tools: dict[str, Any],
    websearch_tools: dict[str, Any],
    callable_registry: dict[str, Callable],
) -> tuple[str, Any] | None:
    """Compile a single node and add to graph.

    Args:
        node_name: Name of the node
        node_config: Node configuration dict
        graph: StateGraph to add node to
        config: Full graph config for defaults
        tools: Shell tools registry
        python_tools: Python tools registry
        websearch_tools: Web search tools registry (LangChain StructuredTool)
        callable_registry: Loaded callable functions for tool_call nodes

    Returns:
        Tuple of (node_name, map_info) for map nodes, None otherwise
    """
    # Copy node config and add loop_limit if specified
    enriched_config = dict(node_config)
    if node_name in config.loop_limits:
        enriched_config["loop_limit"] = config.loop_limits[node_name]

    # Extract prompts path config from defaults (FR-A)
    prompts_relative = config.defaults.get("prompts_relative", False)
    prompts_dir = config.defaults.get("prompts_dir")
    if prompts_dir:
        prompts_dir = Path(prompts_dir)

    node_type = node_config.get("type", NodeType.LLM)

    if node_type == NodeType.TOOL:
        node_fn = create_tool_node(node_name, enriched_config, tools)
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.PYTHON:
        node_fn = create_python_node(node_name, enriched_config, python_tools)
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.AGENT:
        node_fn = create_agent_node(
            node_name, enriched_config, tools, websearch_tools, python_tools
        )
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.MAP:
        map_edge_fn, sub_node_name = compile_map_node(
            node_name,
            enriched_config,
            graph,
            config.defaults,
            callable_registry,
            graph_path=config.source_path,
        )
        logger.info(f"Added node: {node_name} (type={node_type})")
        return (node_name, (map_edge_fn, sub_node_name))
    elif node_type == NodeType.TOOL_CALL:
        # Dynamic tool call from state
        node_fn = create_tool_call_node(node_name, enriched_config, callable_registry)
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.INTERRUPT:
        # Human-in-the-loop interrupt node
        node_fn = create_interrupt_node(
            node_name,
            enriched_config,
            graph_path=config.source_path,
            prompts_dir=prompts_dir,
            prompts_relative=prompts_relative,
        )
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.PASSTHROUGH:
        # Simple state transformation node
        node_fn = create_passthrough_node(node_name, enriched_config)
        graph.add_node(node_name, node_fn)
    elif node_type == NodeType.SUBGRAPH:
        # Subgraph node - compose graphs from YAML
        if not config.source_path:
            raise ValueError(
                f"Cannot resolve subgraph path for node '{node_name}': "
                "parent graph has no source_path"
            )
        node_fn = create_subgraph_node(
            node_name,
            enriched_config,
            parent_graph_path=config.source_path,
        )
        graph.add_node(node_name, node_fn)
    else:
        # LLM and router nodes
        node_fn = create_node_function(
            node_name,
            enriched_config,
            config.defaults,
            graph_path=config.source_path,
        )
        graph.add_node(node_name, node_fn)

    logger.info(f"Added node: {node_name} (type={node_type})")
    return None


def compile_nodes(
    config: "GraphConfig",
    graph: StateGraph,
    tools: dict[str, Any],
    python_tools: dict[str, Any],
    websearch_tools: dict[str, Any],
    callable_registry: dict[str, Callable],
) -> dict[str, tuple]:
    """Compile all nodes and add to graph.

    Args:
        config: Graph configuration
        graph: StateGraph to add nodes to
        tools: Shell tools registry
        python_tools: Python tools registry
        websearch_tools: Web search tools registry
        callable_registry: Loaded callable functions for tool_call nodes

    Returns:
        Dict of map_nodes: name -> (map_edge_fn, sub_node_name)
    """
    map_nodes: dict[str, tuple] = {}

    for node_name, node_config in config.nodes.items():
        result = compile_node(
            node_name,
            node_config,
            graph,
            config,
            tools,
            python_tools,
            websearch_tools,
            callable_registry,
        )
        if result:
            map_nodes[result[0]] = result[1]

    return map_nodes


__all__ = ["compile_node", "compile_nodes"]
