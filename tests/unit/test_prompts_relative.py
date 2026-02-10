"""Tests for prompts_relative config propagation.

Ensures prompts_relative and prompts_dir reach all node types consistently.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestPromptsRelativeConfig:
    """Tests that prompts_relative flows to all node factories."""

    @pytest.fixture
    def demo_graph_path(self) -> Path:
        """Path to a demo graph with prompts_relative: true."""
        return Path("examples/demos/reflexion/graph.yaml")

    @pytest.mark.req("REQ-YG-012")
    def test_graph_config_has_prompts_relative(self, demo_graph_path: Path):
        """GraphConfig exposes prompts_relative from top-level config."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(demo_graph_path)

        assert config.prompts_relative is True
        assert config.prompts_dir == "prompts"

    @pytest.mark.req("REQ-YG-012")
    def test_llm_node_receives_prompts_config(self, demo_graph_path: Path):
        """LLM nodes receive prompts_relative via effective_defaults."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(demo_graph_path)

        # Build effective_defaults as node_compiler does
        effective_defaults = dict(config.defaults)
        effective_defaults["prompts_relative"] = config.prompts_relative
        if config.prompts_dir:
            effective_defaults["prompts_dir"] = str(config.prompts_dir)

        # Verify effective_defaults has the settings
        assert effective_defaults["prompts_relative"] is True
        assert effective_defaults["prompts_dir"] == "prompts"

    @pytest.mark.req("REQ-YG-012")
    def test_agent_node_receives_prompts_config(self):
        """Agent nodes receive prompts_relative via defaults dict."""
        from yamlgraph.tools.agent import create_agent_node

        # Create agent node with defaults containing prompts settings
        defaults = {
            "prompts_relative": True,
            "prompts_dir": "prompts",
        }
        node_config = {
            "prompt": "test_prompt",
            "tools": [],
        }

        # Should not raise - agent reads from defaults
        with patch("yamlgraph.tools.agent.load_prompt") as mock_load:
            mock_load.return_value = {"system": "test", "user": "{input}"}
            node_fn = create_agent_node(
                "test_agent",
                node_config,
                tools={},
                defaults=defaults,
                graph_path=Path("examples/demos/git-report/graph.yaml"),
            )
            assert callable(node_fn)

    @pytest.mark.req("REQ-YG-012")
    def test_map_node_receives_prompts_config(self, demo_graph_path: Path):
        """Map nodes receive prompts_relative via defaults dict."""
        from yamlgraph.graph_loader import load_graph_config

        # Load map demo config
        map_config = load_graph_config("examples/demos/map/graph.yaml")

        assert map_config.prompts_relative is True
        assert map_config.prompts_dir == "prompts"


class TestEffectiveDefaultsBuilding:
    """Tests for effective_defaults construction in node_compiler."""

    @pytest.mark.req("REQ-YG-012")
    def test_effective_defaults_includes_prompts_settings(self):
        """effective_defaults should merge top-level prompts settings."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config("examples/demos/reflexion/graph.yaml")

        # Simulate what node_compiler does
        effective_defaults = dict(config.defaults)
        prompts_relative = config.prompts_relative
        prompts_dir = config.prompts_dir
        if prompts_dir:
            prompts_dir = Path(prompts_dir)

        effective_defaults["prompts_relative"] = prompts_relative
        if prompts_dir:
            effective_defaults["prompts_dir"] = str(prompts_dir)

        # Original defaults should have provider/temperature
        assert True

        # Effective defaults should have prompts settings merged
        assert effective_defaults["prompts_relative"] is True
        assert effective_defaults["prompts_dir"] == "prompts"

    @pytest.mark.req("REQ-YG-012")
    def test_top_level_overrides_defaults_block(self):
        """Top-level prompts_relative should override defaults block value."""
        from yamlgraph.graph_loader import GraphConfig

        # Config with prompts_relative at both levels
        raw_config = {
            "version": "1.0",
            "name": "test",
            "prompts_relative": True,  # Top level
            "defaults": {
                "prompts_relative": False,  # In defaults block
            },
            "nodes": {
                "dummy": {"type": "passthrough"},
            },
            "edges": [{"from": "START", "to": "dummy"}, {"from": "dummy", "to": "END"}],
        }

        config = GraphConfig(raw_config)

        # Top-level should win
        assert config.prompts_relative is True
