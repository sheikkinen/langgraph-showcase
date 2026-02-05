"""Smoke tests for cost-router example."""

from pathlib import Path

import yaml

EXAMPLE_DIR = Path(__file__).parent.parent
GRAPH_PATH = EXAMPLE_DIR / "cost-router.yaml"


class TestGraphStructure:
    """Test graph.yaml structure and validity."""

    def test_graph_yaml_exists(self):
        """Graph file should exist."""
        assert GRAPH_PATH.exists(), f"Missing {GRAPH_PATH}"

    def test_graph_yaml_valid(self):
        """Graph should be valid YAML."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        assert config is not None
        assert config.get("name") == "cost-router"

    def test_has_router_edges(self):
        """Should have conditional router edges."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        edges = config.get("edges", [])
        # Find classify -> router edges
        router_edges = [e for e in edges if e.get("from") == "classify"]
        assert len(router_edges) > 0, "Missing router edges from classify node"

    def test_multi_provider_setup(self):
        """Should use multiple LLM providers."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        nodes = config.get("nodes", {})
        providers = set()
        for node_cfg in nodes.values():
            if "provider" in node_cfg:
                providers.add(node_cfg["provider"])
        # Should have at least 2 different providers
        assert len(providers) >= 2, f"Expected multiple providers, got {providers}"

    def test_prompts_exist(self):
        """Prompt files referenced should exist."""
        prompts_dir = EXAMPLE_DIR / "prompts"
        assert prompts_dir.exists()
        assert (prompts_dir / "classify_complexity.yaml").exists()
        assert (prompts_dir / "execute_query.yaml").exists()


class TestGraphLoader:
    """Test graph can be loaded by yamlgraph."""

    def test_graph_loads(self):
        """Graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(str(GRAPH_PATH))
        assert config is not None
        assert config.name == "cost-router"
