#!/usr/bin/env python3
"""YAMLGraph MCP Server — expose graphs as Copilot/MCP tools.

CAP-19: MCP Server Interface (REQ-YG-066, REQ-YG-067, REQ-YG-068)

Usage (stdio transport):
    python yamlgraph/mcp_server.py

Configure in .mcp.json:
    {
      "mcpServers": {
        "yamlgraph": {
          "command": ".venv/bin/python3",
          "args": ["yamlgraph/mcp_server.py"]
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import glob
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

try:
    import mcp.server.stdio
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.lowlevel.server import NotificationOptions
    from mcp.server.models import InitializationOptions
except ImportError as exc:
    raise ImportError(
        "MCP SDK not installed. Install with: pip install yamlgraph[mcp]"
    ) from exc

logger = logging.getLogger(__name__)

# Default timeout for graph invocation (seconds)
INVOKE_TIMEOUT = 120

# Default graph scan patterns (relative to project root)
DEFAULT_GRAPH_PATTERNS = [
    "examples/demos/*/*.yaml",
    "examples/*/*.yaml",
]

# Thread pool for blocking graph invocations
_executor = ThreadPoolExecutor(max_workers=1)


# ---------------------------------------------------------------------------
# REQ-YG-067: Graph discovery
# ---------------------------------------------------------------------------


def discover_graphs(patterns: list[str]) -> list[dict[str, Any]]:
    """Scan directories for graph YAML files and parse headers.

    A YAML file is considered a graph if it contains a ``nodes`` key.
    This allows discovery of non-standard filenames (e.g. ``pipeline.yaml``,
    ``drill-down.yaml``) while excluding prompt templates.

    Args:
        patterns: Glob patterns to scan for YAML files.

    Returns:
        List of dicts with keys: name, description, path, required_vars.
    """
    graphs: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for pattern in patterns:
        for path_str in sorted(glob.glob(pattern, recursive=True)):
            real = str(Path(path_str).resolve())
            if real in seen_paths:
                continue
            seen_paths.add(real)

            try:
                with open(path_str) as f:
                    config = yaml.safe_load(f)
                if not isinstance(config, dict):
                    continue

                # Only include files that look like graphs (have nodes)
                if "nodes" not in config:
                    continue

                name = config.get("name", Path(path_str).parent.name)
                description = config.get("description", "")
                state = config.get("state", {})
                required_vars = list(state.keys()) if isinstance(state, dict) else []

                graphs.append(
                    {
                        "name": name,
                        "description": description,
                        "path": str(Path(path_str).resolve()),
                        "required_vars": required_vars,
                    }
                )
            except Exception:
                logger.warning("Failed to parse %s", path_str, exc_info=True)

    return graphs


# ---------------------------------------------------------------------------
# REQ-YG-068: Graph invocation
# ---------------------------------------------------------------------------


def _invoke_graph(graph_path: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Load, compile, and invoke a graph synchronously.

    Args:
        graph_path: Absolute path to graph.yaml.
        variables: Input variables for the graph.

    Returns:
        Result dict from graph invocation.
    """
    from yamlgraph.graph_loader import compile_graph, load_graph_config

    config = load_graph_config(graph_path)
    sg = compile_graph(config)
    compiled = sg.compile()
    result = compiled.invoke(variables)
    return result


# ---------------------------------------------------------------------------
# REQ-YG-066: MCP server with stdio transport
# ---------------------------------------------------------------------------


def create_server(
    graph_patterns: list[str] | None = None,
) -> Server:
    """Create and configure the MCP server.

    Args:
        graph_patterns: Glob patterns for graph discovery.
            Defaults to DEFAULT_GRAPH_PATTERNS.

    Returns:
        Configured MCP Server instance.
    """
    if graph_patterns is None:
        graph_patterns = DEFAULT_GRAPH_PATTERNS

    graphs = discover_graphs(graph_patterns)
    graph_lookup: dict[str, dict[str, Any]] = {g["name"]: g for g in graphs}

    server = Server("yamlgraph")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List yamlgraph_list_graphs and yamlgraph_run_graph tools."""
        return [
            types.Tool(
                name="yamlgraph_list_graphs",
                description=(
                    "List available YAMLGraph graphs with descriptions "
                    "and required variables."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="yamlgraph_run_graph",
                description=(
                    "Run a YAMLGraph pipeline by name. Pass variables "
                    "required by the graph."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "graph": {
                            "type": "string",
                            "description": ("Graph name (from yamlgraph_list_graphs)"),
                        },
                        "vars": {
                            "type": "object",
                            "description": "Input variables for the graph",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "required": ["graph"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent]:
        """Route tool calls to handlers."""
        try:
            if name == "yamlgraph_list_graphs":
                return _handle_list_graphs(graphs)
            elif name == "yamlgraph_run_graph":
                return await _handle_run_graph(arguments, graph_lookup)
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({"error": f"Unknown tool: {name}"}),
                    )
                ]
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e, exc_info=True)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}),
                )
            ]

    return server


def _handle_list_graphs(
    graphs: list[dict[str, Any]],
) -> list[types.TextContent]:
    """Return graph list as JSON."""
    summary = [
        {
            "name": g["name"],
            "description": g["description"],
            "required_vars": g["required_vars"],
        }
        for g in graphs
    ]
    return [types.TextContent(type="text", text=json.dumps(summary, indent=2))]


async def _handle_run_graph(
    arguments: dict[str, Any],
    graph_lookup: dict[str, dict[str, Any]],
) -> list[types.TextContent]:
    """Invoke a graph and return result as JSON."""
    graph_name = arguments.get("graph", "")
    variables = arguments.get("vars", {})

    if graph_name not in graph_lookup:
        available = list(graph_lookup.keys())
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Graph '{graph_name}' not found",
                        "available": available,
                    }
                ),
            )
        ]

    graph_info = graph_lookup[graph_name]
    graph_path = graph_info["path"]

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, _invoke_graph, graph_path, variables),
            timeout=INVOKE_TIMEOUT,
        )
    except TimeoutError:
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"error": f"Graph '{graph_name}' timed out after {INVOKE_TIMEOUT}s"}
                ),
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": f"Graph execution failed: {e}"}),
            )
        ]

    # Serialize result — filter non-serializable values
    serializable = {}
    for k, v in result.items():
        try:
            json.dumps(v)
            serializable[k] = v
        except (TypeError, ValueError):
            serializable[k] = str(v)

    return [types.TextContent(type="text", text=json.dumps(serializable, indent=2))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the MCP server with stdio transport."""
    # Resolve patterns relative to this file's parent (project root)
    project_root = Path(__file__).resolve().parent.parent
    patterns = [str(project_root / p) for p in DEFAULT_GRAPH_PATTERNS]

    server = create_server(graph_patterns=patterns)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="yamlgraph",
                server_version="0.4.39",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
