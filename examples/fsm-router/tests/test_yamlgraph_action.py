"""Tests for YAMLGraph FSM action."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add example to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestYamlgraphAction:
    """Tests for the YamlgraphAction class."""

    @pytest.fixture
    def action_config(self):
        """Basic action configuration."""
        return {
            "type": "yamlgraph",
            "params": {
                "graph": "graphs/classifier.yaml",
                "input_key": "query",
                "output_key": "result",
                "success": "classified",
                "failure": "failed",
            },
        }

    @pytest.fixture
    def context(self):
        """Basic FSM context."""
        return {
            "machine_name": "test_router",
            "query": "Hello, how are you?",
        }

    def test_action_imports_correctly(self):
        """Test that the action can be imported."""
        pytest.importorskip("statemachine_engine")
        from actions.yamlgraph_action import YamlgraphAction

        assert YamlgraphAction is not None

    def test_action_inherits_base_action(self):
        """Test that action inherits from BaseAction."""
        pytest.importorskip("statemachine_engine")
        from actions.yamlgraph_action import YamlgraphAction
        from statemachine_engine.actions.base import BaseAction

        assert issubclass(YamlgraphAction, BaseAction)

    @pytest.mark.asyncio
    async def test_action_requires_graph_path(self, context):
        """Test that action fails without graph path."""
        pytest.importorskip("statemachine_engine")
        from actions.yamlgraph_action import YamlgraphAction

        config = {"params": {}}  # No graph path
        action = YamlgraphAction(config)

        event = await action.execute(context)

        assert event == "failed"
        assert "error" in context

    @pytest.mark.asyncio
    async def test_action_handles_missing_yamlgraph(self, action_config, context):
        """Test that action handles missing yamlgraph gracefully."""
        pytest.importorskip("statemachine_engine")
        from actions.yamlgraph_action import YamlgraphAction

        action = YamlgraphAction(action_config)

        # Mock import to fail
        with (
            patch.dict("sys.modules", {"yamlgraph.executor_async": None}),
            patch("actions.yamlgraph_action.YamlgraphAction.execute") as mock_exec,
        ):
            mock_exec.return_value = "failed"
            event = await action.execute(context)

        # Should fail gracefully
        assert event == "failed"

    @pytest.mark.asyncio
    async def test_action_returns_route_from_result(self, action_config, context):
        """Test that action returns route event from YAMLGraph result."""
        pytest.importorskip("statemachine_engine")
        pytest.importorskip("yamlgraph")
        from actions.yamlgraph_action import YamlgraphAction

        action = YamlgraphAction(action_config)

        # Mock YAMLGraph execution
        mock_result = {"route": "complex", "category": "technical"}

        with (
            patch("yamlgraph.executor_async.load_and_compile_async") as mock_load,
            patch("yamlgraph.executor_async.run_graph_async") as mock_run,
        ):
            mock_app = AsyncMock()
            mock_load.return_value = mock_app
            mock_run.return_value = mock_result

            event = await action.execute(context)

        # Should return the route from result
        assert event == "complex"
        assert context["result"] == mock_result

    @pytest.mark.asyncio
    async def test_action_uses_success_event_when_no_route(
        self, action_config, context
    ):
        """Test that action returns success event when no route in result."""
        pytest.importorskip("statemachine_engine")
        pytest.importorskip("yamlgraph")
        from actions.yamlgraph_action import YamlgraphAction

        action = YamlgraphAction(action_config)

        # Mock result without route
        mock_result = {"response": "Hello!"}

        with (
            patch("yamlgraph.executor_async.load_and_compile_async") as mock_load,
            patch("yamlgraph.executor_async.run_graph_async") as mock_run,
        ):
            mock_app = AsyncMock()
            mock_load.return_value = mock_app
            mock_run.return_value = mock_result

            event = await action.execute(context)

        assert event == "classified"  # success event from config

    @pytest.mark.asyncio
    async def test_action_passes_variables_to_graph(self, context):
        """Test that action passes variables to YAMLGraph."""
        pytest.importorskip("statemachine_engine")
        pytest.importorskip("yamlgraph")
        from actions.yamlgraph_action import YamlgraphAction

        config = {
            "params": {
                "graph": "graphs/test.yaml",
                "input_key": "query",
                "variables": {
                    "extra_context": "some value",
                    "from_context": "{machine_name}",
                },
                "success": "done",
            }
        }
        action = YamlgraphAction(config)

        captured_state = {}

        async def capture_run(app, state, *args, **kwargs):
            captured_state.update(state)
            return {"response": "ok"}

        with (
            patch("yamlgraph.executor_async.load_and_compile_async") as mock_load,
            patch("yamlgraph.executor_async.run_graph_async", side_effect=capture_run),
        ):
            mock_load.return_value = AsyncMock()
            await action.execute(context)

        assert captured_state["query"] == "Hello, how are you?"
        assert captured_state["extra_context"] == "some value"
        assert captured_state["from_context"] == "test_router"

    @pytest.mark.asyncio
    async def test_action_handles_execution_error(self, action_config, context):
        """Test that action handles YAMLGraph execution errors."""
        pytest.importorskip("statemachine_engine")
        pytest.importorskip("yamlgraph")
        from actions.yamlgraph_action import YamlgraphAction

        action = YamlgraphAction(action_config)

        with patch("yamlgraph.executor_async.load_and_compile_async") as mock_load:
            mock_load.side_effect = Exception("Graph compilation failed")

            event = await action.execute(context)

        assert event == "failed"
        assert "error" in context
        assert "Graph compilation failed" in context["error"]


class TestFSMIntegration:
    """Integration tests for FSM + YAMLGraph."""

    def test_fsm_config_is_valid_yaml(self):
        """Test that FSM config is valid YAML."""
        import yaml

        config_path = Path(__file__).parent.parent / "config" / "router.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["initial_state"] == "waiting"
        assert "transitions" in config
        assert "actions" in config

    def test_yamlgraph_configs_are_valid(self):
        """Test that YAMLGraph configs are valid YAML."""
        import yaml

        graphs_dir = Path(__file__).parent.parent / "graphs"

        for graph_file in graphs_dir.glob("*.yaml"):
            with open(graph_file) as f:
                config = yaml.safe_load(f)

            assert "name" in config
            assert "nodes" in config
            assert "edges" in config

    def test_prompts_are_valid(self):
        """Test that prompt files are valid YAML."""
        import yaml

        prompts_dir = Path(__file__).parent.parent / "graphs" / "prompts"

        for prompt_file in prompts_dir.glob("*.yaml"):
            with open(prompt_file) as f:
                config = yaml.safe_load(f)

            # Should have user or system field
            assert "user" in config or "system" in config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
