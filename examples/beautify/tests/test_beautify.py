"""Smoke tests for beautify example."""

from pathlib import Path

import yaml

EXAMPLE_DIR = Path(__file__).parent.parent
GRAPH_PATH = EXAMPLE_DIR / "graph.yaml"


class TestGraphStructure:
    """Test graph.yaml structure and validity."""

    def test_graph_yaml_exists(self):
        """Graph file should exist."""
        assert GRAPH_PATH.exists(), f"Missing {GRAPH_PATH}"

    def test_graph_yaml_valid(self):
        """Graph should be valid YAML."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        assert config is not None
        assert config.get("name") == "beautify"

    def test_required_nodes_present(self):
        """Required nodes should be defined."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        nodes = config.get("nodes", {})
        required = ["load_graph", "analyze", "mermaid", "render_html", "save_output"]
        for node in required:
            assert node in nodes, f"Missing node: {node}"

    def test_prompts_exist(self):
        """Prompt files referenced should exist."""
        prompts_dir = EXAMPLE_DIR / "prompts"
        assert prompts_dir.exists()
        assert (prompts_dir / "analyze.yaml").exists()
        assert (prompts_dir / "mermaid.yaml").exists()


class TestGraphLoader:
    """Test graph can be loaded by yamlgraph."""

    def test_graph_loads(self):
        """Graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(str(GRAPH_PATH))
        assert config is not None
        assert config.name == "beautify"

    def test_tools_defined(self):
        """Python tools should be defined."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        tools = config.get("tools", {})
        assert "load_graph" in tools
        assert "render_html" in tools
        assert "save_output" in tools


class TestNodeFunctions:
    """Test node function imports."""

    def test_load_graph_import(self):
        """load_graph function should be importable."""
        from examples.beautify.nodes import load_graph

        assert callable(load_graph)

    def test_render_html_import(self):
        """render_html function should be importable."""
        from examples.beautify.nodes import render_html

        assert callable(render_html)

    def test_save_output_import(self):
        """save_output function should be importable."""
        from examples.beautify.nodes import save_output

        assert callable(save_output)
