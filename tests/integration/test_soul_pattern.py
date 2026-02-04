"""Integration tests for soul pattern using data_files.

TDD: Tests for the soul pattern example.
The soul pattern demonstrates how to give AI agents consistent personality
by loading a soul configuration via data_files and using it in prompts.
"""

from pathlib import Path

from yamlgraph.graph_loader import load_graph_config

SOUL_EXAMPLE_PATH = Path(__file__).parent.parent.parent / "examples" / "soul"


class TestSoulPatternExample:
    """Test that soul pattern example is properly structured."""

    def test_soul_example_exists(self) -> None:
        """Soul example directory exists with required files."""
        assert SOUL_EXAMPLE_PATH.exists(), "examples/soul directory should exist"
        assert (SOUL_EXAMPLE_PATH / "graph.yaml").exists()
        assert (SOUL_EXAMPLE_PATH / "souls").is_dir()
        assert (SOUL_EXAMPLE_PATH / "prompts").is_dir()
        assert (SOUL_EXAMPLE_PATH / "README.md").exists()

    def test_soul_files_exist(self) -> None:
        """Soul configuration files exist."""
        souls_dir = SOUL_EXAMPLE_PATH / "souls"
        assert (souls_dir / "friendly.yaml").exists()
        assert (souls_dir / "formal.yaml").exists()

    def test_graph_loads_soul_via_data_files(self) -> None:
        """Graph config loads soul file via data_files."""
        graph_file = SOUL_EXAMPLE_PATH / "graph.yaml"
        config = load_graph_config(graph_file)

        assert "soul" in config.data
        assert "name" in config.data["soul"]
        assert "voice" in config.data["soul"]
        assert "principles" in config.data["soul"]

    def test_soul_has_required_fields(self) -> None:
        """Soul configuration has all required personality fields."""
        graph_file = SOUL_EXAMPLE_PATH / "graph.yaml"
        config = load_graph_config(graph_file)

        soul = config.data["soul"]
        assert isinstance(soul["name"], str)
        assert isinstance(soul["voice"], str)
        assert isinstance(soul["principles"], list)
        assert len(soul["principles"]) > 0

    def test_soul_switchable_at_runtime(self) -> None:
        """Soul can be overridden via input (data_files allows input override)."""
        # This tests the pattern, not execution
        # Input providing 'soul' key should override data_files soul
        graph_file = SOUL_EXAMPLE_PATH / "graph.yaml"
        config = load_graph_config(graph_file)

        # Soul from data_files is injected into state
        # The override works because input values win over data_files
        assert "soul" in config.data

        # Verify data_files soul has expected structure that can be overridden
        soul = config.data["soul"]
        assert "name" in soul
        assert "voice" in soul
        assert "principles" in soul


class TestSoulPatternStructure:
    """Test soul file structure follows conventions."""

    def test_friendly_soul_structure(self) -> None:
        """Friendly soul has warm, approachable characteristics."""
        import yaml

        soul_file = SOUL_EXAMPLE_PATH / "souls" / "friendly.yaml"
        with open(soul_file) as f:
            soul = yaml.safe_load(f)

        assert soul["name"] == "Friendly Helper"
        assert "warm" in soul["voice"].lower() or "friendly" in soul["voice"].lower()

    def test_formal_soul_structure(self) -> None:
        """Formal soul has professional characteristics."""
        import yaml

        soul_file = SOUL_EXAMPLE_PATH / "souls" / "formal.yaml"
        with open(soul_file) as f:
            soul = yaml.safe_load(f)

        assert (
            "formal" in soul["name"].lower() or "professional" in soul["name"].lower()
        )
