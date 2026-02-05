"""Smoke tests for book_translator example."""

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
        assert config.get("name") == "book-translator"

    def test_has_checkpointer(self):
        """Should have SQLite checkpointer for long-running jobs."""
        config = yaml.safe_load(GRAPH_PATH.read_text())
        assert "checkpointer" in config
        assert config["checkpointer"]["type"] == "sqlite"

    def test_prompts_exist(self):
        """Prompt files referenced should exist."""
        prompts_dir = EXAMPLE_DIR / "prompts"
        assert prompts_dir.exists()
        # Check key prompts exist
        prompt_files = list(prompts_dir.glob("*.yaml"))
        assert len(prompt_files) > 0, "No prompt files found"


class TestGraphLoader:
    """Test graph can be loaded by yamlgraph."""

    def test_graph_loads(self):
        """Graph should load without errors."""
        from yamlgraph.graph_loader import load_graph_config

        config = load_graph_config(str(GRAPH_PATH))
        assert config is not None
        assert config.name == "book-translator"


class TestToolFunctions:
    """Test tool function imports."""

    def test_split_by_markers_import(self):
        """split_by_markers function should be importable."""
        from examples.book_translator.nodes.tools import split_by_markers

        assert callable(split_by_markers)

    def test_merge_terms_import(self):
        """merge_terms function should be importable."""
        from examples.book_translator.nodes.tools import merge_terms

        assert callable(merge_terms)

    def test_check_scores_import(self):
        """check_scores function should be importable."""
        from examples.book_translator.nodes.tools import check_scores

        assert callable(check_scores)

    def test_join_chunks_import(self):
        """join_chunks function should be importable."""
        from examples.book_translator.nodes.tools import join_chunks

        assert callable(join_chunks)


class TestModels:
    """Test dataclass models."""

    def test_models_import(self):
        """Models should be importable."""
        from examples.book_translator.models import Chunk

        assert Chunk is not None
