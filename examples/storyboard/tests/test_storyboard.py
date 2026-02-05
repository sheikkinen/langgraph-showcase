"""Smoke tests for storyboard example."""

from pathlib import Path

import pytest
import yaml

EXAMPLE_DIR = Path(__file__).parent.parent


class TestGraphStructure:
    """Test graph YAML files structure and validity."""

    @pytest.mark.parametrize(
        "graph_file",
        [
            "graph.yaml",
            "character-graph.yaml",
            "animated-character-graph.yaml",
        ],
    )
    def test_graph_yaml_exists(self, graph_file):
        """Graph files should exist."""
        path = EXAMPLE_DIR / graph_file
        assert path.exists(), f"Missing {path}"

    def test_main_graph_valid(self):
        """Main graph should be valid."""
        config = yaml.safe_load((EXAMPLE_DIR / "graph.yaml").read_text())
        assert config.get("name") == "storyboard"
        nodes = config.get("nodes", {})
        assert "expand_story" in nodes
        assert "generate_images" in nodes

    def test_prompts_exist(self):
        """Prompt files referenced should exist."""
        prompts_dir = EXAMPLE_DIR / "prompts"
        assert prompts_dir.exists()
        # Check key prompts exist
        prompt_files = list(prompts_dir.glob("*.yaml"))
        assert len(prompt_files) > 0, "No prompt files found"


class TestGraphLoader:
    """Test graph can be loaded by yamlgraph."""

    def test_main_graph_loads(self):
        """Main graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(str(EXAMPLE_DIR / "graph.yaml"))
        assert config is not None
        assert config.name == "storyboard"

    def test_character_graph_loads(self):
        """Character graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(str(EXAMPLE_DIR / "character-graph.yaml"))
        assert config is not None


class TestNodeFunctions:
    """Test node function imports."""

    def test_image_node_import(self):
        """Image node function should be importable."""
        from examples.storyboard.nodes.image_node import generate_images_node

        assert callable(generate_images_node)
