"""Tests for MCP server — CAP-19: MCP Server Interface.

TDD red phase: all tests written before implementation.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Guard: mcp is an optional dependency
mcp = pytest.importorskip("mcp")
from mcp import types  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers for calling MCP server handlers in unit tests
# ---------------------------------------------------------------------------


async def _call_list_tools(server):
    """Invoke the registered list_tools handler."""
    handler = server.request_handlers[types.ListToolsRequest]
    req = types.ListToolsRequest(method="tools/list")
    result = await handler(req)
    return result.root.tools


async def _call_tool(server, name: str, arguments: dict):
    """Invoke the registered call_tool handler."""
    handler = server.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(name=name, arguments=arguments),
    )
    result = await handler(req)
    return result.root.content


# ---------------------------------------------------------------------------
# REQ-YG-067: Graph discovery
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-067")
def test_discover_graphs_finds_yaml(tmp_path: Path):
    """Scan dirs find graph.yaml files and parse headers."""
    from yamlgraph.mcp_server import discover_graphs

    # Create a minimal graph.yaml
    graph_dir = tmp_path / "demo"
    graph_dir.mkdir()
    (graph_dir / "graph.yaml").write_text(
        "version: '1.0'\nname: test-graph\n"
        "description: A test graph\n"
        "state:\n  topic: str\n"
        "nodes:\n  greet:\n    type: llm\n    prompt: greet\n    state_key: greeting\n"
        "edges:\n  - from: START\n    to: greet\n  - from: greet\n    to: END\n"
    )

    graphs = discover_graphs([str(tmp_path / "*/graph.yaml")])
    assert len(graphs) == 1
    assert graphs[0]["name"] == "test-graph"
    assert graphs[0]["description"] == "A test graph"


@pytest.mark.req("REQ-YG-067")
def test_discover_graphs_non_standard_filename(tmp_path: Path):
    """Discover graph YAML files with non-standard names like pipeline.yaml."""
    from yamlgraph.mcp_server import discover_graphs

    graph_dir = tmp_path / "demo"
    graph_dir.mkdir()
    (graph_dir / "pipeline.yaml").write_text(
        "version: '1.0'\nname: my-pipeline\n"
        "description: A pipeline graph\n"
        "state:\n  domain: str\n"
        "nodes:\n  n1:\n    type: llm\n    prompt: p\n    state_key: out\n"
        "edges:\n  - from: START\n    to: n1\n  - from: n1\n    to: END\n"
    )
    # Also create a prompt YAML (no nodes key) — must be excluded
    prompts_dir = graph_dir / "prompts"
    prompts_dir.mkdir()

    graphs = discover_graphs([str(tmp_path / "demo/*.yaml")])
    assert len(graphs) == 1
    assert graphs[0]["name"] == "my-pipeline"


@pytest.mark.req("REQ-YG-067")
def test_discover_graphs_skips_prompt_yaml(tmp_path: Path):
    """Prompt YAML files (no nodes key) are excluded from discovery."""
    from yamlgraph.mcp_server import discover_graphs

    graph_dir = tmp_path / "demo"
    graph_dir.mkdir()
    (graph_dir / "prompt.yaml").write_text(
        "metadata:\n  name: greet\n" "system: You are helpful.\n" "user: Hello {name}\n"
    )

    graphs = discover_graphs([str(tmp_path / "demo/*.yaml")])
    assert graphs == []


@pytest.mark.req("REQ-YG-067")
def test_discover_graphs_empty_dir(tmp_path: Path):
    """Empty or missing dir returns empty list."""
    from yamlgraph.mcp_server import discover_graphs

    graphs = discover_graphs([str(tmp_path / "nonexistent/*/*.yaml")])
    assert graphs == []


@pytest.mark.req("REQ-YG-067")
def test_discover_graphs_parses_state(tmp_path: Path):
    """Extracts state vars as parameter info."""
    from yamlgraph.mcp_server import discover_graphs

    graph_dir = tmp_path / "myapp"
    graph_dir.mkdir()
    (graph_dir / "graph.yaml").write_text(
        "version: '1.0'\nname: stateful\n"
        "description: Has state vars\n"
        "state:\n  topic: str\n  depth: int\n"
        "nodes:\n  n1:\n    type: llm\n    prompt: p\n    state_key: out\n"
        "edges:\n  - from: START\n    to: n1\n  - from: n1\n    to: END\n"
    )

    graphs = discover_graphs([str(tmp_path / "*/graph.yaml")])
    assert len(graphs) == 1
    assert "topic" in graphs[0]["required_vars"]
    assert "depth" in graphs[0]["required_vars"]


# ---------------------------------------------------------------------------
# REQ-YG-066: MCP server tools schema
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-066")
@pytest.mark.asyncio
async def test_list_tools_schema():
    """Tool list includes correct names and input schemas."""
    from yamlgraph.mcp_server import create_server

    server = create_server(graph_patterns=[])
    tools = await _call_list_tools(server)
    tool_names = {t.name for t in tools}
    assert "yamlgraph_list_graphs" in tool_names
    assert "yamlgraph_run_graph" in tool_names

    # Verify run_graph has graph + vars in schema
    run_tool = next(t for t in tools if t.name == "yamlgraph_run_graph")
    props = run_tool.inputSchema["properties"]
    assert "graph" in props
    assert "vars" in props


# ---------------------------------------------------------------------------
# REQ-YG-068: Graph invocation via MCP
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-068")
@pytest.mark.asyncio
async def test_run_graph_hello():
    """Invoke hello graph via MCP, returns greeting in result."""
    from yamlgraph.mcp_server import create_server

    hello_pattern = str(
        Path(__file__).resolve().parent.parent.parent
        / "examples"
        / "demos"
        / "hello"
        / "graph.yaml"
    )
    server = create_server(graph_patterns=[hello_pattern])

    # Mock the graph invocation to avoid real LLM calls
    mock_result = {"greeting": "Hello World!"}
    with patch("yamlgraph.mcp_server._invoke_graph", return_value=mock_result):
        result = await _call_tool(
            server,
            "yamlgraph_run_graph",
            {
                "graph": "hello-world",
                "vars": {"name": "World", "style": "enthusiastic"},
            },
        )

    assert len(result) == 1
    parsed = json.loads(result[0].text)
    assert "greeting" in parsed


@pytest.mark.req("REQ-YG-068")
@pytest.mark.asyncio
async def test_run_graph_missing():
    """Missing graph returns error, doesn't crash server."""
    from yamlgraph.mcp_server import create_server

    server = create_server(graph_patterns=[])
    result = await _call_tool(
        server,
        "yamlgraph_run_graph",
        {"graph": "nonexistent-graph", "vars": {}},
    )

    assert len(result) == 1
    parsed = json.loads(result[0].text)
    assert "error" in parsed


@pytest.mark.req("REQ-YG-068")
@pytest.mark.asyncio
async def test_run_graph_with_vars():
    """Vars passed through to graph state correctly."""
    from yamlgraph.mcp_server import create_server

    hello_pattern = str(
        Path(__file__).resolve().parent.parent.parent
        / "examples"
        / "demos"
        / "hello"
        / "graph.yaml"
    )
    server = create_server(graph_patterns=[hello_pattern])

    captured_vars = {}

    def fake_invoke(graph_path: str, variables: dict) -> dict:
        captured_vars.update(variables)
        return {"greeting": "mocked"}

    with patch("yamlgraph.mcp_server._invoke_graph", side_effect=fake_invoke):
        await _call_tool(
            server,
            "yamlgraph_run_graph",
            {"graph": "hello-world", "vars": {"name": "Test", "style": "formal"}},
        )

    assert captured_vars["name"] == "Test"
    assert captured_vars["style"] == "formal"


@pytest.mark.req("REQ-YG-068")
@pytest.mark.asyncio
async def test_run_graph_timeout():
    """Graph timeout produces error result, not hang."""
    from yamlgraph.mcp_server import create_server

    hello_pattern = str(
        Path(__file__).resolve().parent.parent.parent
        / "examples"
        / "demos"
        / "hello"
        / "graph.yaml"
    )
    server = create_server(graph_patterns=[hello_pattern])

    def slow_invoke(graph_path: str, variables: dict) -> dict:
        import time

        time.sleep(10)  # simulate slow graph
        return {}

    with (
        patch("yamlgraph.mcp_server._invoke_graph", side_effect=slow_invoke),
        patch("yamlgraph.mcp_server.INVOKE_TIMEOUT", 0.1),
    ):
        result = await _call_tool(
            server,
            "yamlgraph_run_graph",
            {"graph": "hello-world", "vars": {"name": "X", "style": "Y"}},
        )

    assert len(result) == 1
    parsed = json.loads(result[0].text)
    assert "error" in parsed
