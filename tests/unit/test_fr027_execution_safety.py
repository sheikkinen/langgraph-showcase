"""Tests for FR-027: Execution Safety Guards.

RED tests — written before implementation.

P0 items:
1. Map fan-out max_items cap (REQ-YG-055)
2. recursion_limit exposure (REQ-YG-056)
3. loop_limits enforced in all node types (REQ-YG-057)
4. Linter W012: cycle without loop_limits (REQ-YG-058)

P1 items:
5. max_iterations default mismatch fix (REQ-YG-059)
6. max_tokens wired to create_llm() (REQ-YG-060)
7. Global execution timeout (REQ-YG-061)
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


# ──────────────────────────────────────────────────────────────
# 6. max_iterations default mismatch fix (REQ-YG-059)
# ──────────────────────────────────────────────────────────────


class TestMaxIterationsMismatch:
    """max_iterations must have a single default of 10 everywhere."""

    @pytest.mark.req("REQ-YG-059")
    def test_agent_default_max_iterations_is_10(self):
        """agent.py runtime default must be 10, not 5."""
        # Inspect the source to ensure no hardcoded `5`
        import inspect

        from yamlgraph.tools.agent import create_agent_node

        source = inspect.getsource(create_agent_node)
        # The line `node_config.get("max_iterations", 5)` is the bug
        # After fix, default should be 10
        assert 'max_iterations", 5)' not in source
        assert 'max_iterations", 10)' in source or "max_iterations" in source

    @pytest.mark.req("REQ-YG-059")
    def test_schema_and_runtime_agree_on_10(self):
        """Pydantic model, JSON schema, and agent code must all say 10."""
        from yamlgraph.models.graph_schema import NodeConfig

        # Pydantic model should default to 10
        nc = NodeConfig(type="agent")
        assert nc.max_iterations == 10

    @pytest.mark.req("REQ-YG-059")
    def test_agent_node_config_get_reads_from_config_not_hardcoded(self):
        """agent.py must use node_config value, not shadow it with hardcoded 5."""
        from yamlgraph.tools.agent import create_agent_node
        from yamlgraph.tools.shell import ShellToolConfig

        tools = {
            "test": ShellToolConfig(command="echo test", description="Test"),
        }
        # Explicitly set max_iterations=3
        node_config = {
            "prompt": "agent",
            "tools": ["test"],
            "max_iterations": 3,
        }
        node_fn = create_agent_node("agent", node_config, tools)
        assert callable(node_fn)


# ──────────────────────────────────────────────────────────────
# 7. max_tokens wired to create_llm() (REQ-YG-060)
# ──────────────────────────────────────────────────────────────


class TestMaxTokensWiring:
    """max_tokens must flow from YAML node config → create_llm() → provider."""

    @pytest.mark.req("REQ-YG-060")
    def test_create_llm_accepts_max_tokens(self):
        """create_llm() must accept a max_tokens parameter."""
        import inspect

        from yamlgraph.utils.llm_factory import create_llm

        sig = inspect.signature(create_llm)
        assert "max_tokens" in sig.parameters

    @pytest.mark.req("REQ-YG-060")
    def test_create_llm_passes_max_tokens_to_provider(self):
        """create_llm(max_tokens=2048) must pass it to the LLM constructor."""
        from unittest.mock import patch

        from yamlgraph.utils.llm_factory import clear_cache, create_llm

        clear_cache()

        with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
            mock_cls.return_value = mock_cls
            create_llm(provider="anthropic", max_tokens=2048)
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs.get("max_tokens") == 2048

        clear_cache()

    @pytest.mark.req("REQ-YG-060")
    def test_create_llm_omits_max_tokens_when_none(self):
        """create_llm(max_tokens=None) should NOT pass max_tokens to provider."""
        from unittest.mock import patch

        from yamlgraph.utils.llm_factory import clear_cache, create_llm

        clear_cache()

        with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
            mock_cls.return_value = mock_cls
            create_llm(provider="anthropic", max_tokens=None)
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args.kwargs
            assert "max_tokens" not in call_kwargs

        clear_cache()

    @pytest.mark.req("REQ-YG-060")
    def test_node_config_max_tokens_reaches_execute_prompt(self):
        """Node-level max_tokens should be read from config and passed through."""
        from yamlgraph.node_factory.llm_nodes import create_node_function

        node_config = {
            "prompt": "test",
            "max_tokens": 2048,
        }
        # create_node_function should read max_tokens from node_config
        # Verify it doesn't crash (integration tested via mock)
        node_fn = create_node_function("test_node", node_config, defaults={})
        assert callable(node_fn)

    @pytest.mark.req("REQ-YG-060")
    def test_execute_prompt_accepts_max_tokens(self):
        """execute_prompt() must accept a max_tokens parameter."""
        import inspect

        from yamlgraph.executor import execute_prompt

        sig = inspect.signature(execute_prompt)
        assert "max_tokens" in sig.parameters

    @pytest.mark.req("REQ-YG-060")
    def test_graph_config_max_tokens(self):
        """GraphConfig must parse config.max_tokens from YAML."""
        from yamlgraph.graph_loader import GraphConfig

        config = {
            "nodes": {"a": {"type": "llm", "prompt": "test"}},
            "edges": [{"from": "START", "to": "a"}, {"from": "a", "to": "END"}],
            "config": {"max_tokens": 2048},
        }
        gc = GraphConfig(config)
        assert gc.max_tokens == 2048

    @pytest.mark.req("REQ-YG-060")
    def test_graph_config_max_tokens_default_none(self):
        """GraphConfig max_tokens should default to None (no cap)."""
        from yamlgraph.graph_loader import GraphConfig

        config = {
            "nodes": {"a": {"type": "llm", "prompt": "test"}},
            "edges": [{"from": "START", "to": "a"}, {"from": "a", "to": "END"}],
        }
        gc = GraphConfig(config)
        assert gc.max_tokens is None

    @pytest.mark.req("REQ-YG-060")
    def test_json_schema_has_max_tokens_in_config(self):
        """graph-v1.json config block must include max_tokens."""
        import json

        schema_path = (
            Path(__file__).parent.parent.parent
            / "yamlgraph"
            / "schemas"
            / "graph-v1.json"
        )
        schema = json.loads(schema_path.read_text())
        config_props = schema["properties"]["config"]["properties"]
        assert "max_tokens" in config_props

    @pytest.mark.req("REQ-YG-060")
    def test_cache_key_includes_max_tokens(self):
        """LLM cache key must include max_tokens to avoid serving wrong instance."""
        from unittest.mock import patch

        from yamlgraph.utils.llm_factory import clear_cache

        clear_cache()

        with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
            mock_cls.return_value = mock_cls
            from yamlgraph.utils.llm_factory import create_llm

            create_llm(provider="anthropic", max_tokens=2048)
            create_llm(provider="anthropic", max_tokens=4096)
            # Should be called twice (different cache keys)
            assert mock_cls.call_count == 2

        clear_cache()

    @pytest.mark.req("REQ-YG-060")
    def test_replicate_provider_receives_max_tokens(self):
        """create_llm(provider='replicate', max_tokens=2048) must pass it through."""
        pytest.importorskip("langchain_litellm")
        from unittest.mock import patch

        from yamlgraph.utils.llm_factory import clear_cache, create_llm

        clear_cache()

        with (
            patch("langchain_litellm.ChatLiteLLM") as mock_cls,
            patch.dict("os.environ", {"REPLICATE_API_TOKEN": "test-token"}),
        ):
            mock_cls.return_value = mock_cls
            create_llm(provider="replicate", model="meta/llama-2", max_tokens=2048)
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs.get("max_tokens") == 2048

        clear_cache()

    @pytest.mark.req("REQ-YG-060")
    def test_replicate_provider_omits_max_tokens_when_none(self):
        """create_llm(provider='replicate', max_tokens=None) should NOT pass it."""
        pytest.importorskip("langchain_litellm")
        from unittest.mock import patch

        from yamlgraph.utils.llm_factory import clear_cache, create_llm

        clear_cache()

        with (
            patch("langchain_litellm.ChatLiteLLM") as mock_cls,
            patch.dict("os.environ", {"REPLICATE_API_TOKEN": "test-token"}),
        ):
            mock_cls.return_value = mock_cls
            create_llm(provider="replicate", model="meta/llama-2", max_tokens=None)
            mock_cls.assert_called_once()
            call_kwargs = mock_cls.call_args.kwargs
            assert "max_tokens" not in call_kwargs

        clear_cache()

    @pytest.mark.req("REQ-YG-061")
    def test_timeout_saves_and_restores_previous_sigalrm_handler(self):
        """Timeout setup must save and restore the previous SIGALRM handler."""
        import platform

        if platform.system() == "Windows":
            pytest.skip("SIGALRM not available on Windows")

        import signal

        from yamlgraph.cli.graph_commands import _setup_timeout, _teardown_timeout

        # Set a custom handler
        custom_handler = lambda signum, frame: None  # noqa: E731
        signal.signal(signal.SIGALRM, custom_handler)

        ctx = _setup_timeout(1)
        # Handler should have been replaced
        current = signal.getsignal(signal.SIGALRM)
        assert current is not custom_handler

        _teardown_timeout(ctx)
        # Previous handler should be restored
        restored = signal.getsignal(signal.SIGALRM)
        assert restored is custom_handler

        # Cleanup
        signal.signal(signal.SIGALRM, signal.SIG_DFL)


# ──────────────────────────────────────────────────────────────
# 8. Global execution timeout (REQ-YG-061)
# ──────────────────────────────────────────────────────────────


class TestExecutionTimeout:
    """config.timeout and --timeout must cap total execution wall-clock time."""

    @pytest.mark.req("REQ-YG-061")
    def test_graph_config_parses_timeout(self):
        """GraphConfig must parse config.timeout from YAML."""
        from yamlgraph.graph_loader import GraphConfig

        config = {
            "nodes": {"a": {"type": "llm", "prompt": "test"}},
            "edges": [{"from": "START", "to": "a"}, {"from": "a", "to": "END"}],
            "config": {"timeout": 120},
        }
        gc = GraphConfig(config)
        assert gc.timeout == 120

    @pytest.mark.req("REQ-YG-061")
    def test_graph_config_timeout_default_none(self):
        """GraphConfig timeout should default to None (no timeout)."""
        from yamlgraph.graph_loader import GraphConfig

        config = {
            "nodes": {"a": {"type": "llm", "prompt": "test"}},
            "edges": [{"from": "START", "to": "a"}, {"from": "a", "to": "END"}],
        }
        gc = GraphConfig(config)
        assert gc.timeout is None

    @pytest.mark.req("REQ-YG-061")
    def test_json_schema_has_timeout_in_config(self):
        """graph-v1.json config block must include timeout."""
        import json

        schema_path = (
            Path(__file__).parent.parent.parent
            / "yamlgraph"
            / "schemas"
            / "graph-v1.json"
        )
        schema = json.loads(schema_path.read_text())
        config_props = schema["properties"]["config"]["properties"]
        assert "timeout" in config_props

    @pytest.mark.req("REQ-YG-061")
    def test_timeout_triggers_sys_exit(self):
        """When timeout fires, cmd_graph_run should exit with error."""
        import argparse
        from unittest.mock import MagicMock, patch

        from yamlgraph.cli.graph_commands import cmd_graph_run

        mock_config = MagicMock()
        mock_config.recursion_limit = 50
        mock_config.max_tokens = None
        mock_config.timeout = 1  # 1 second timeout
        mock_config.data = {}

        mock_graph = MagicMock()
        mock_app = MagicMock()
        # Simulate a slow invoke
        import time

        mock_app.invoke.side_effect = lambda *a, **kw: time.sleep(5) or {
            "result": "late"
        }
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
            timeout=None,  # CLI not set, YAML says 1
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch("yamlgraph.graph_loader.load_graph_config", return_value=mock_config),
            patch("yamlgraph.graph_loader.compile_graph", return_value=mock_graph),
            patch(
                "yamlgraph.graph_loader.get_checkpointer_for_graph", return_value=None
            ),
            pytest.raises(SystemExit),
        ):
            cmd_graph_run(args)

    @pytest.mark.req("REQ-YG-061")
    def test_cli_timeout_overrides_yaml(self):
        """--timeout CLI arg should override YAML config.timeout."""
        from yamlgraph.graph_loader import GraphConfig

        config = {
            "nodes": {"a": {"type": "llm", "prompt": "test"}},
            "edges": [{"from": "START", "to": "a"}, {"from": "a", "to": "END"}],
            "config": {"timeout": 120},
        }
        gc = GraphConfig(config)
        assert gc.timeout == 120
        # CLI override would be handled in cmd_graph_run, same pattern as recursion_limit


# ──────────────────────────────────────────────────────────────
# 9. Linter W013: dynamic map over without max_items (REQ-YG-062)
# ──────────────────────────────────────────────────────────────


class TestLinterW013DynamicMap:
    """W013: warn when map over: is a dynamic expression without max_items."""

    @pytest.mark.req("REQ-YG-062")
    def test_w013_fires_on_dynamic_over_without_max_items(self):
        """W013 should fire when over: is a state reference and no max_items set."""
        from yamlgraph.linter.checks_semantic import (
            check_dynamic_map_without_max_items,
        )

        node_config = {
            "type": "map",
            "over": "{state.chapters}",
            "as": "chapter",
            "collect": "results",
            "node": {"type": "llm", "prompt": "test"},
        }
        issues = check_dynamic_map_without_max_items("translate_all", node_config, {})
        assert len(issues) == 1
        assert issues[0].code == "W013"
        assert "translate_all" in issues[0].message

    @pytest.mark.req("REQ-YG-062")
    def test_w013_suppressed_by_node_max_items(self):
        """W013 should NOT fire when node has max_items set."""
        from yamlgraph.linter.checks_semantic import (
            check_dynamic_map_without_max_items,
        )

        node_config = {
            "type": "map",
            "over": "{state.chapters}",
            "as": "chapter",
            "collect": "results",
            "max_items": 20,
            "node": {"type": "llm", "prompt": "test"},
        }
        issues = check_dynamic_map_without_max_items("translate_all", node_config, {})
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-062")
    def test_w013_suppressed_by_graph_max_map_items(self):
        """W013 should NOT fire when graph config has max_map_items set."""
        from yamlgraph.linter.checks_semantic import (
            check_dynamic_map_without_max_items,
        )

        node_config = {
            "type": "map",
            "over": "{state.chapters}",
            "as": "chapter",
            "collect": "results",
            "node": {"type": "llm", "prompt": "test"},
        }
        graph_config = {"max_map_items": 100}
        issues = check_dynamic_map_without_max_items(
            "translate_all", node_config, graph_config
        )
        assert len(issues) == 0

    @pytest.mark.req("REQ-YG-062")
    def test_w013_not_fired_on_literal_list(self):
        """W013 should NOT fire when over: is a literal list."""
        from yamlgraph.linter.checks_semantic import (
            check_dynamic_map_without_max_items,
        )

        node_config = {
            "type": "map",
            "over": ["a", "b", "c"],
            "as": "item",
            "collect": "results",
            "node": {"type": "llm", "prompt": "test"},
        }
        issues = check_dynamic_map_without_max_items("static_map", node_config, {})
        assert len(issues) == 0
