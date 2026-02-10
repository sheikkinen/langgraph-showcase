"""Integration tests for python-map demo (FR-021).

Tests the type:python sub-node in map nodes feature.
"""

from pathlib import Path

import pytest

from yamlgraph.graph_loader import compile_graph, load_graph_config

DEMO_PATH = Path(__file__).parent.parent.parent / "examples" / "demos" / "python-map"


class TestPythonMapDemo:
    """Test python-map demo structure and compilation."""

    @pytest.mark.req("REQ-YG-020", "REQ-YG-040")
    def test_demo_exists(self) -> None:
        """Demo directory exists with required files."""
        assert DEMO_PATH.exists(), "examples/demos/python-map should exist"
        assert (DEMO_PATH / "graph.yaml").exists()
        assert (DEMO_PATH / "tools.py").exists()
        assert (DEMO_PATH / "README.md").exists()

    @pytest.mark.req("REQ-YG-020", "REQ-YG-040")
    def test_graph_loads(self) -> None:
        """Graph config loads successfully."""
        config = load_graph_config(DEMO_PATH / "graph.yaml")
        assert config.name == "python-map-demo"

    @pytest.mark.req("REQ-YG-020", "REQ-YG-040")
    def test_graph_has_map_node(self) -> None:
        """Graph has a map node with python sub-node."""
        config = load_graph_config(DEMO_PATH / "graph.yaml")
        assert "analyze" in config.nodes
        assert config.nodes["analyze"]["type"] == "map"
        assert config.nodes["analyze"]["node"]["type"] == "python"

    @pytest.mark.req("REQ-YG-020", "REQ-YG-040")
    def test_graph_compiles(self) -> None:
        """Graph compiles without errors."""
        config = load_graph_config(DEMO_PATH / "graph.yaml")
        graph = compile_graph(config)
        assert graph is not None

    @pytest.mark.req("REQ-YG-020", "REQ-YG-040")
    def test_tools_module_importable(self) -> None:
        """Tools module can be imported."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "python_map_tools", DEMO_PATH / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert callable(module.analyze_text)

    @pytest.mark.req("REQ-YG-020", "REQ-YG-040")
    def test_analyze_text_function(self) -> None:
        """analyze_text returns expected structure."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "python_map_tools", DEMO_PATH / "tools.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        result = module.analyze_text({"text": "Hello world!"})
        assert "stats" in result
        assert result["stats"]["word_count"] == 2
        assert result["stats"]["char_count"] == 12
