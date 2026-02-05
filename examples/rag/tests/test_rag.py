"""Smoke tests for rag example."""

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
        assert config.get("name") == "rag-example"

    def test_required_nodes_present(self):
        """Required nodes should be defined."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        nodes = config.get("nodes", {})
        required = ["setup", "retrieve", "answer"]
        for node in required:
            assert node in nodes, f"Missing node: {node}"

    def test_rag_tool_defined(self):
        """RAG retrieve tool should be defined."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        tools = config.get("tools", {})
        assert "rag_retrieve" in tools

    def test_prompts_exist(self):
        """Prompt files referenced should exist."""
        prompts_dir = EXAMPLE_DIR / "prompts"
        assert prompts_dir.exists()
        assert (prompts_dir / "answer.yaml").exists()


class TestGraphLoader:
    """Test graph can be loaded by yamlgraph."""

    def test_graph_loads(self):
        """Graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(str(GRAPH_PATH))
        assert config is not None
        assert config.name == "rag-example"


class TestToolFunctions:
    """Test tool function imports."""

    def test_rag_retrieve_import(self):
        """rag_retrieve function should be importable."""
        # Tool is in tools/ relative to example
        import sys

        sys.path.insert(0, str(EXAMPLE_DIR))
        try:
            from tools.rag_retrieve import rag_retrieve_node

            assert callable(rag_retrieve_node)
        finally:
            sys.path.pop(0)
