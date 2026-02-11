"""Tests for FR-027: Execution Safety Guards.

RED tests — written before implementation.

P0 items:
1. Map fan-out max_items cap (REQ-YG-055)
2. recursion_limit exposure (REQ-YG-056)
3. loop_limits enforced in all node types (REQ-YG-057)
4. Linter W012: cycle without loop_limits (REQ-YG-058)
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ──────────────────────────────────────────────────────────────
# 1. Map fan-out max_items cap (REQ-YG-055)
# ──────────────────────────────────────────────────────────────


class TestMapMaxItems:
    """Map node fan-out should be capped by max_items."""

    @pytest.mark.req("REQ-YG-055")
    def test_map_edge_truncates_items_to_max_items(self):
        """When items list exceeds max_items, truncate + warn."""
        # Build a minimal graph + config
        from langgraph.graph import StateGraph

        from yamlgraph.map_compiler import compile_map_node
        from yamlgraph.models.state_builder import build_state_class

        state_class = build_state_class(
            {"items": "list", "results": "list", "current_step": "str"}
        )
        builder = StateGraph(state_class)

        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "max_items": 3,
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }

        map_edge, _sub = compile_map_node(
            "test_map",
            config,
            builder,
            defaults={"provider": "openai"},
        )

        # Create state with 10 items
        state = {"items": list(range(10)), "results": [], "current_step": ""}
        sends = map_edge(state)

        # Should only fan out to 3 items
        assert len(sends) == 3

    @pytest.mark.req("REQ-YG-055")
    def test_map_edge_respects_graph_level_default(self):
        """Graph-level max_map_items used when node has no max_items."""
        from langgraph.graph import StateGraph

        from yamlgraph.map_compiler import compile_map_node
        from yamlgraph.models.state_builder import build_state_class

        state_class = build_state_class(
            {"items": "list", "results": "list", "current_step": "str"}
        )
        builder = StateGraph(state_class)

        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            # No max_items on node
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }

        map_edge, _sub = compile_map_node(
            "test_map",
            config,
            builder,
            defaults={"provider": "openai", "max_map_items": 5},
        )

        state = {"items": list(range(20)), "results": [], "current_step": ""}
        sends = map_edge(state)

        # Should cap at graph-level default of 5
        assert len(sends) == 5

    @pytest.mark.req("REQ-YG-055")
    def test_map_edge_no_truncation_within_limit(self):
        """When items <= max_items, no truncation occurs."""
        from langgraph.graph import StateGraph

        from yamlgraph.map_compiler import compile_map_node
        from yamlgraph.models.state_builder import build_state_class

        state_class = build_state_class(
            {"items": "list", "results": "list", "current_step": "str"}
        )
        builder = StateGraph(state_class)

        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            "max_items": 100,
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }

        map_edge, _sub = compile_map_node(
            "test_map",
            config,
            builder,
            defaults={"provider": "openai"},
        )

        state = {"items": [1, 2, 3], "results": [], "current_step": ""}
        sends = map_edge(state)

        assert len(sends) == 3

    @pytest.mark.req("REQ-YG-055")
    def test_map_edge_default_100_cap(self):
        """Without explicit config, default cap is 100."""
        from langgraph.graph import StateGraph

        from yamlgraph.map_compiler import compile_map_node
        from yamlgraph.models.state_builder import build_state_class

        state_class = build_state_class(
            {"items": "list", "results": "list", "current_step": "str"}
        )
        builder = StateGraph(state_class)

        config = {
            "over": "{items}",
            "as": "item",
            "collect": "results",
            # No max_items, no defaults.max_map_items
            "node": {"type": "llm", "prompt": "test", "state_key": "result"},
        }

        map_edge, _sub = compile_map_node(
            "test_map",
            config,
            builder,
            defaults={"provider": "openai"},
        )

        state = {"items": list(range(200)), "results": [], "current_step": ""}
        sends = map_edge(state)

        # Default cap should be 100
        assert len(sends) == 100


# ──────────────────────────────────────────────────────────────
# 2. recursion_limit exposure (REQ-YG-056)
# ──────────────────────────────────────────────────────────────


class TestRecursionLimit:
    """recursion_limit should be configurable via YAML config: section."""

    @pytest.mark.req("REQ-YG-056")
    def test_graph_config_reads_recursion_limit(self):
        """GraphConfig should parse config.recursion_limit from YAML."""
        from yamlgraph.graph_loader import GraphConfig

        raw = {
            "nodes": {"a": {"type": "llm", "prompt": "test"}},
            "edges": [{"from": "START", "to": "a"}, {"from": "a", "to": "END"}],
            "config": {"recursion_limit": 25},
        }
        gc = GraphConfig(raw)
        assert gc.recursion_limit == 25

    @pytest.mark.req("REQ-YG-056")
    def test_graph_config_default_recursion_limit(self):
        """Default recursion_limit should be 50."""
        from yamlgraph.graph_loader import GraphConfig

        raw = {
            "nodes": {"a": {"type": "llm", "prompt": "test"}},
            "edges": [{"from": "START", "to": "a"}, {"from": "a", "to": "END"}],
        }
        gc = GraphConfig(raw)
        assert gc.recursion_limit == 50

    @pytest.mark.req("REQ-YG-056")
    def test_graph_config_reads_max_map_items(self):
        """GraphConfig should parse config.max_map_items."""
        from yamlgraph.graph_loader import GraphConfig

        raw = {
            "nodes": {"a": {"type": "llm", "prompt": "test"}},
            "edges": [{"from": "START", "to": "a"}, {"from": "a", "to": "END"}],
            "config": {"max_map_items": 42},
        }
        gc = GraphConfig(raw)
        assert gc.max_map_items == 42


# ──────────────────────────────────────────────────────────────
# 3. loop_limits enforced in all node types (REQ-YG-057)
# ──────────────────────────────────────────────────────────────


class TestLoopLimitsAllNodeTypes:
    """check_loop_limit should be enforced in tool, python, passthrough nodes."""

    @pytest.mark.req("REQ-YG-057")
    def test_tool_node_checks_loop_limit(self):
        """Tool node should return _loop_limit_reached when count >= limit."""
        from yamlgraph.tools.nodes import create_tool_node
        from yamlgraph.tools.shell import ShellToolConfig

        tools = {"echo": ShellToolConfig(command="echo hello", description="test")}
        node_config = {
            "tool": "echo",
            "state_key": "output",
            "loop_limit": 2,
        }
        node_fn = create_tool_node("test_tool", node_config, tools)

        # Simulate loop count at limit
        state = {"_loop_counts": {"test_tool": 2}, "output": None}
        result = node_fn(state)

        assert result.get("_loop_limit_reached") is True

    @pytest.mark.req("REQ-YG-057")
    def test_tool_node_increments_loop_count(self):
        """Tool node should increment _loop_counts on execution."""
        from yamlgraph.tools.nodes import create_tool_node
        from yamlgraph.tools.shell import ShellToolConfig

        tools = {"echo": ShellToolConfig(command="echo hello", description="test")}
        node_config = {
            "tool": "echo",
            "state_key": "output",
            "loop_limit": 5,
        }
        node_fn = create_tool_node("test_tool", node_config, tools)

        state = {"_loop_counts": {"test_tool": 0}, "output": None}
        result = node_fn(state)

        assert result["_loop_counts"]["test_tool"] == 1

    @pytest.mark.req("REQ-YG-057")
    def test_python_node_checks_loop_limit(self):
        """Python node should return _loop_limit_reached at limit."""
        from yamlgraph.tools.python_tool import PythonToolConfig, create_python_node

        python_tools = {
            "my_func": PythonToolConfig(
                module="builtins", function="str", description="test"
            )
        }
        node_config = {
            "tool": "my_func",
            "state_key": "output",
            "loop_limit": 2,
        }
        node_fn = create_python_node("test_py", node_config, python_tools)

        state = {"_loop_counts": {"test_py": 2}, "output": None}
        result = node_fn(state)

        assert result.get("_loop_limit_reached") is True

    @pytest.mark.req("REQ-YG-057")
    def test_python_node_increments_loop_count(self):
        """Python node should increment _loop_counts on execution."""
        from yamlgraph.tools.python_tool import PythonToolConfig, create_python_node

        python_tools = {
            "my_func": PythonToolConfig(
                module="builtins", function="str", description="test"
            )
        }
        node_config = {
            "tool": "my_func",
            "state_key": "output",
            "loop_limit": 10,
        }
        node_fn = create_python_node("test_py", node_config, python_tools)

        state = {"_loop_counts": {"test_py": 0}, "output": None}
        result = node_fn(state)

        assert result["_loop_counts"]["test_py"] == 1

    @pytest.mark.req("REQ-YG-057")
    def test_passthrough_node_checks_loop_limit(self):
        """Passthrough node should return _loop_limit_reached at limit."""
        from yamlgraph.node_factory.control_nodes import create_passthrough_node

        config = {
            "output": {"counter": "{state.counter + 1}"},
            "loop_limit": 3,
        }
        node_fn = create_passthrough_node("test_pass", config)

        state = {"_loop_counts": {"test_pass": 3}, "counter": 5}
        result = node_fn(state)

        assert result.get("_loop_limit_reached") is True

    @pytest.mark.req("REQ-YG-057")
    def test_passthrough_node_increments_loop_count(self):
        """Passthrough node should increment _loop_counts on execution."""
        from yamlgraph.node_factory.control_nodes import create_passthrough_node

        config = {
            "output": {"counter": "{state.counter + 1}"},
            "loop_limit": 10,
        }
        node_fn = create_passthrough_node("test_pass", config)

        state = {"_loop_counts": {"test_pass": 0}, "counter": 5}
        result = node_fn(state)

        assert result["_loop_counts"]["test_pass"] == 1


# ──────────────────────────────────────────────────────────────
# 4. Linter W012: cycle without loop_limits (REQ-YG-058)
# ──────────────────────────────────────────────────────────────


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "linter"


class TestLinterW012:
    """Linter should warn when a cycle node has no loop_limits entry."""

    @pytest.mark.req("REQ-YG-058")
    def test_w012_fires_on_unguarded_cycle(self):
        """Cycle without loop_limits should produce W012 warnings."""
        from yamlgraph.linter.checks_semantic import check_unguarded_cycles

        issues = check_unguarded_cycles(FIXTURES_DIR / "cycle_unguarded_fail.yaml")

        codes = [i.code for i in issues]
        assert "W012" in codes
        # Both cycle nodes (generate, critique) should be flagged
        messages = " ".join(i.message for i in issues)
        assert "generate" in messages
        assert "critique" in messages

    @pytest.mark.req("REQ-YG-058")
    def test_w012_does_not_fire_on_guarded_cycle(self):
        """Cycle with loop_limits should NOT produce W012."""
        from yamlgraph.linter.checks_semantic import check_unguarded_cycles

        issues = check_unguarded_cycles(FIXTURES_DIR / "cycle_guarded_pass.yaml")

        codes = [i.code for i in issues]
        assert "W012" not in codes

    @pytest.mark.req("REQ-YG-058")
    def test_w012_registered_in_lint_graph(self):
        """lint_graph should include W012 checks."""
        from yamlgraph.linter.graph_linter import lint_graph

        result = lint_graph(FIXTURES_DIR / "cycle_unguarded_fail.yaml")

        codes = [i.code for i in result.issues]
        assert "W012" in codes

    @pytest.mark.req("REQ-YG-058")
    def test_w012_no_false_positive_on_acyclic(self):
        """Acyclic graph should produce no W012."""
        from yamlgraph.linter.checks_semantic import check_unguarded_cycles

        # Use an existing simple graph fixture
        issues = check_unguarded_cycles(FIXTURES_DIR / "retry_tool_pass.yaml")

        codes = [i.code for i in issues]
        assert "W012" not in codes


# ──────────────────────────────────────────────────────────────
# 5. recursion_limit wired to graph.invoke() (REQ-YG-056)
# ──────────────────────────────────────────────────────────────


class TestRecursionLimitWiring:
    """recursion_limit must flow from YAML/CLI to app.invoke(config=...)."""

    @pytest.mark.req("REQ-YG-056")
    def test_yaml_recursion_limit_reaches_invoke(self):
        """YAML config.recursion_limit should be passed to app.invoke()."""
        import argparse
        from unittest.mock import MagicMock, patch

        from yamlgraph.cli.graph_commands import cmd_graph_run

        mock_config = MagicMock()
        mock_config.recursion_limit = 25
        mock_config.data = {}

        mock_graph = MagicMock()
        mock_app = MagicMock()
        mock_app.invoke.return_value = {"result": "ok"}
        mock_graph.compile.return_value = mock_app

        args = argparse.Namespace(
            graph_path="examples/demos/hello/graph.yaml",
            var=[],
            thread=None,
            export=False,
            use_async=False,
            share_trace=False,
            full=False,
            recursion_limit=None,  # Not set via CLI
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "yamlgraph.graph_loader.load_graph_config",
                return_value=mock_config,
            ),
            patch(
                "yamlgraph.graph_loader.compile_graph",
                return_value=mock_graph,
            ),
            patch(
                "yamlgraph.graph_loader.get_checkpointer_for_graph",
                return_value=None,
            ),
        ):
            cmd_graph_run(args)

        # Verify recursion_limit=25 was passed in config
        invoke_kwargs = mock_app.invoke.call_args
        config_passed = invoke_kwargs.kwargs.get("config")
        assert config_passed["recursion_limit"] == 25

    @pytest.mark.req("REQ-YG-056")
    def test_cli_recursion_limit_overrides_yaml(self):
        """--recursion-limit CLI arg should override YAML config."""
        import argparse
        from unittest.mock import MagicMock, patch

        from yamlgraph.cli.graph_commands import cmd_graph_run

        mock_config = MagicMock()
        mock_config.recursion_limit = 25  # YAML says 25
        mock_config.data = {}

        mock_graph = MagicMock()
        mock_app = MagicMock()
        mock_app.invoke.return_value = {"result": "ok"}
        mock_graph.compile.return_value = mock_app

        args = argparse.Namespace(
            graph_path="examples/demos/hello/graph.yaml",
            var=[],
            thread=None,
            export=False,
            use_async=False,
            share_trace=False,
            full=False,
            recursion_limit=10,  # CLI override
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "yamlgraph.graph_loader.load_graph_config",
                return_value=mock_config,
            ),
            patch(
                "yamlgraph.graph_loader.compile_graph",
                return_value=mock_graph,
            ),
            patch(
                "yamlgraph.graph_loader.get_checkpointer_for_graph",
                return_value=None,
            ),
        ):
            cmd_graph_run(args)

        # CLI value 10 should override YAML value 25
        invoke_kwargs = mock_app.invoke.call_args
        config_passed = invoke_kwargs.kwargs.get("config")
        assert config_passed["recursion_limit"] == 10

    @pytest.mark.req("REQ-YG-056")
    def test_default_recursion_limit_50_reaches_invoke(self):
        """When neither CLI nor YAML sets it, default 50 should reach invoke."""
        import argparse
        from unittest.mock import MagicMock, patch

        from yamlgraph.cli.graph_commands import cmd_graph_run

        mock_config = MagicMock()
        mock_config.recursion_limit = 50  # Default from GraphConfig
        mock_config.data = {}

        mock_graph = MagicMock()
        mock_app = MagicMock()
        mock_app.invoke.return_value = {"result": "ok"}
        mock_graph.compile.return_value = mock_app

        args = argparse.Namespace(
            graph_path="examples/demos/hello/graph.yaml",
            var=[],
            thread=None,
            export=False,
            use_async=False,
            share_trace=False,
            full=False,
            recursion_limit=None,
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch(
                "yamlgraph.graph_loader.load_graph_config",
                return_value=mock_config,
            ),
            patch(
                "yamlgraph.graph_loader.compile_graph",
                return_value=mock_graph,
            ),
            patch(
                "yamlgraph.graph_loader.get_checkpointer_for_graph",
                return_value=None,
            ),
        ):
            cmd_graph_run(args)

        invoke_kwargs = mock_app.invoke.call_args
        config_passed = invoke_kwargs.kwargs.get("config")
        assert config_passed["recursion_limit"] == 50
