"""Smoke tests for npc example."""

from pathlib import Path

import pytest
import yaml

EXAMPLE_DIR = Path(__file__).parent.parent


class TestGraphStructure:
    """Test graph YAML files structure and validity."""

    @pytest.mark.parametrize(
        "graph_file",
        [
            "npc-creation.yaml",
            "encounter-loop.yaml",
            "encounter-multi.yaml",
            "encounter-turn.yaml",
        ],
    )
    def test_graph_yaml_exists(self, graph_file):
        """Graph files should exist."""
        path = EXAMPLE_DIR / graph_file
        assert path.exists(), f"Missing {path}"

    def test_npc_creation_valid(self):
        """NPC creation graph should be valid."""
        config = yaml.safe_load((EXAMPLE_DIR / "npc-creation.yaml").read_text())
        assert config.get("name") == "npc-creation"
        nodes = config.get("nodes", {})
        required = ["identity", "personality", "knowledge", "behavior"]
        for node in required:
            assert node in nodes, f"Missing node: {node}"

    def test_prompts_exist(self):
        """Prompt files referenced should exist."""
        prompts_dir = EXAMPLE_DIR / "prompts"
        assert prompts_dir.exists()
        # Check key prompts exist
        prompt_files = list(prompts_dir.glob("*.yaml"))
        assert len(prompt_files) >= 4, f"Expected 4+ prompts, found {len(prompt_files)}"


class TestGraphLoader:
    """Test graphs can be loaded by yamlgraph."""

    def test_npc_creation_loads(self):
        """NPC creation graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(str(EXAMPLE_DIR / "npc-creation.yaml"))
        assert config is not None
        assert config.name == "npc-creation"

    def test_encounter_loop_loads(self):
        """Encounter loop graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(str(EXAMPLE_DIR / "encounter-loop.yaml"))
        assert config is not None


class TestNodeFunctions:
    """Test node function imports."""

    def test_nodes_module_import(self):
        """Nodes module should be importable."""
        from examples.npc import nodes

        assert nodes is not None
