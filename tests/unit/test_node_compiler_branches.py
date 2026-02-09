"""Tests for node_compiler.compile_node branch coverage (REQ-YG-007).

Each node type (TOOL, PYTHON, AGENT, MAP, TOOL_CALL, INTERRUPT,
PASSTHROUGH, SUBGRAPH, LLM/router default) is routed to the correct
factory function.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langgraph.graph import StateGraph

from yamlgraph.constants import NodeType
from yamlgraph.graph_loader import GraphConfig
from yamlgraph.node_compiler import compile_node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    nodes: dict | None = None,
    source_path: Path | None = None,
    defaults: dict | None = None,
) -> GraphConfig:
    """Build a minimal valid GraphConfig without hitting real validation."""
    raw = {
        "nodes": nodes or {"dummy": {"prompt": "p", "state_key": "k"}},
        "edges": [{"from": "START", "to": "dummy"}, {"from": "dummy", "to": "END"}],
    }
    if defaults:
        raw["defaults"] = defaults
    cfg = GraphConfig(raw, source_path=source_path)
    return cfg


def _make_graph():
    """Create a StateGraph with a simple state schema."""
    from typing import TypedDict

    class S(TypedDict):
        x: str

    return StateGraph(S)


# ---------------------------------------------------------------------------
# Tests — one per node-type branch
# ---------------------------------------------------------------------------


class TestCompileNodeTool:
    """type=tool → create_tool_node."""

    @patch("yamlgraph.node_compiler.create_tool_node", return_value=lambda s: {})
    def test_tool_branch(self, mock_factory):
        config = _make_config()
        graph = _make_graph()
        node_cfg = {"type": NodeType.TOOL, "tool": "my_tool", "state_key": "out"}

        result = compile_node(
            "t",
            node_cfg,
            graph,
            config,
            tools={"my_tool": MagicMock()},
            python_tools={},
            callable_registry={},
        )

        assert result is None  # non-map nodes return None
        mock_factory.assert_called_once()
        assert "t" in [n for n, _ in graph.nodes.items()]


class TestCompileNodePython:
    """type=python → create_python_node."""

    @patch("yamlgraph.node_compiler.create_python_node", return_value=lambda s: {})
    def test_python_branch(self, mock_factory):
        config = _make_config()
        graph = _make_graph()
        node_cfg = {"type": NodeType.PYTHON, "function": "mod.fn", "state_key": "out"}

        result = compile_node(
            "p",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={"mod.fn": MagicMock()},
            callable_registry={},
        )

        assert result is None
        mock_factory.assert_called_once()


class TestCompileNodeAgent:
    """type=agent → create_agent_node."""

    @patch("yamlgraph.node_compiler.create_agent_node", return_value=lambda s: {})
    def test_agent_branch(self, mock_factory):
        config = _make_config(source_path=Path("/g/graph.yaml"))
        graph = _make_graph()
        node_cfg = {
            "type": NodeType.AGENT,
            "prompt": "agent_prompt",
            "state_key": "out",
        }

        result = compile_node(
            "a",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={},
            callable_registry={},
        )

        assert result is None
        mock_factory.assert_called_once()
        _, kwargs = mock_factory.call_args
        assert kwargs["graph_path"] == Path("/g/graph.yaml")


class TestCompileNodeMap:
    """type=map → compile_map_node (returns map info)."""

    @patch("yamlgraph.node_compiler.compile_map_node")
    def test_map_branch_returns_tuple(self, mock_factory):
        mock_edge_fn = MagicMock()
        mock_factory.return_value = (mock_edge_fn, "sub_node")

        config = _make_config()
        graph = _make_graph()
        node_cfg = {
            "type": NodeType.MAP,
            "iterate_key": "items",
            "state_key": "results",
            "node": {"prompt": "p"},
        }

        result = compile_node(
            "m",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={},
            callable_registry={},
        )

        assert result is not None
        assert result == ("m", (mock_edge_fn, "sub_node"))
        mock_factory.assert_called_once()


class TestCompileNodeToolCall:
    """type=tool_call → create_tool_call_node."""

    @patch("yamlgraph.node_compiler.create_tool_call_node", return_value=lambda s: {})
    def test_tool_call_branch(self, mock_factory):
        config = _make_config()
        graph = _make_graph()
        node_cfg = {
            "type": NodeType.TOOL_CALL,
            "tool": "{state.tool_name}",
            "args": {},
            "state_key": "out",
        }

        result = compile_node(
            "tc",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={},
            callable_registry={"fn": lambda: None},
        )

        assert result is None
        mock_factory.assert_called_once()


class TestCompileNodeInterrupt:
    """type=interrupt → create_interrupt_node."""

    @patch("yamlgraph.node_compiler.create_interrupt_node", return_value=lambda s: {})
    def test_interrupt_branch(self, mock_factory):
        config = _make_config(source_path=Path("/g/graph.yaml"))
        graph = _make_graph()
        node_cfg = {
            "type": NodeType.INTERRUPT,
            "message": "Please confirm",
            "state_key": "confirmation",
        }

        result = compile_node(
            "i",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={},
            callable_registry={},
        )

        assert result is None
        mock_factory.assert_called_once()


class TestCompileNodePassthrough:
    """type=passthrough → create_passthrough_node."""

    @patch("yamlgraph.node_compiler.create_passthrough_node", return_value=lambda s: {})
    def test_passthrough_branch(self, mock_factory):
        config = _make_config()
        graph = _make_graph()
        node_cfg = {
            "type": NodeType.PASSTHROUGH,
            "state_key": "counter",
            "value": 0,
        }

        result = compile_node(
            "pt",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={},
            callable_registry={},
        )

        assert result is None
        mock_factory.assert_called_once()


class TestCompileNodeSubgraph:
    """type=subgraph → create_subgraph_node."""

    @patch("yamlgraph.node_compiler.create_subgraph_node", return_value=lambda s: {})
    def test_subgraph_branch(self, mock_factory):
        config = _make_config(source_path=Path("/g/graph.yaml"))
        graph = _make_graph()
        node_cfg = {
            "type": NodeType.SUBGRAPH,
            "graph": "sub.yaml",
            "state_key": "sub_out",
        }

        result = compile_node(
            "sg",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={},
            callable_registry={},
        )

        assert result is None
        mock_factory.assert_called_once()
        args, kwargs = mock_factory.call_args
        assert kwargs["parent_graph_path"] == Path("/g/graph.yaml")

    def test_subgraph_without_source_path_raises(self):
        """Subgraph node requires parent graph to have source_path."""
        config = _make_config(source_path=None)  # no source_path
        graph = _make_graph()
        node_cfg = {"type": NodeType.SUBGRAPH, "graph": "sub.yaml", "state_key": "out"}

        with pytest.raises(ValueError, match="source_path"):
            compile_node(
                "sg",
                node_cfg,
                graph,
                config,
                tools={},
                python_tools={},
                callable_registry={},
            )


class TestCompileNodeLLMDefault:
    """type=llm (default) → create_node_function."""

    @patch("yamlgraph.node_compiler.create_node_function", return_value=lambda s: {})
    def test_llm_default_branch(self, mock_factory):
        config = _make_config()
        graph = _make_graph()
        node_cfg = {"prompt": "generate", "state_key": "generated"}  # no explicit type

        result = compile_node(
            "llm",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={},
            callable_registry={},
        )

        assert result is None
        mock_factory.assert_called_once()

    @patch("yamlgraph.node_compiler.create_node_function", return_value=lambda s: {})
    def test_router_uses_default_branch(self, mock_factory):
        """Router nodes also go through create_node_function."""
        config = _make_config()
        graph = _make_graph()
        node_cfg = {"type": NodeType.ROUTER, "prompt": "route", "state_key": "route"}

        result = compile_node(
            "router",
            node_cfg,
            graph,
            config,
            tools={},
            python_tools={},
            callable_registry={},
        )

        assert result is None
        mock_factory.assert_called_once()


class TestCompileNodeDefaults:
    """Defaults and loop_limits are propagated correctly."""

    @patch("yamlgraph.node_compiler.create_node_function", return_value=lambda s: {})
    def test_loop_limit_injected(self, mock_factory):
        """Loop limits from config are merged into node config."""
        raw = {
            "nodes": {"n": {"prompt": "p", "state_key": "k"}},
            "edges": [{"from": "START", "to": "n"}, {"from": "n", "to": "END"}],
            "loop_limits": {"n": 5},
        }
        config = GraphConfig(raw)
        graph = _make_graph()
        node_cfg = {"prompt": "p", "state_key": "k"}

        compile_node("n", node_cfg, graph, config, {}, {}, {})

        # The enriched_config passed to factory should contain loop_limit
        call_args = mock_factory.call_args[0]
        enriched = call_args[1]  # second positional arg is enriched_config
        assert enriched.get("loop_limit") == 5

    @patch("yamlgraph.node_compiler.create_node_function", return_value=lambda s: {})
    def test_prompts_relative_propagated(self, mock_factory):
        """prompts_relative from config.defaults flows to effective_defaults."""
        config = _make_config(
            defaults={"prompts_relative": True, "provider": "anthropic"},
            source_path=Path("/g/graph.yaml"),
        )
        graph = _make_graph()
        node_cfg = {"prompt": "p", "state_key": "k"}

        compile_node("n", node_cfg, graph, config, {}, {}, {})

        call_args = mock_factory.call_args
        defaults_arg = call_args[0][2]  # third positional arg is defaults
        assert defaults_arg["prompts_relative"] is True
