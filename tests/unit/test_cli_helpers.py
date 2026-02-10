"""Tests for CLI helpers."""

from pathlib import Path

import pytest

from yamlgraph.cli.helpers import (
    GraphLoadError,
    load_graph_config,
    require_graph_config,
)


class TestLoadGraphConfig:
    """Test load_graph_config helper."""

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_loads_valid_yaml(self, tmp_path: Path):
        """Should load valid YAML graph config."""
        graph_file = tmp_path / "test.yaml"
        graph_file.write_text("""
name: test-graph
nodes:
  greet:
    prompt: greet
edges:
  - from: START
    to: greet
""")
        config = load_graph_config(graph_file)

        assert config["name"] == "test-graph"
        assert "greet" in config["nodes"]

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_raises_on_missing_file(self, tmp_path: Path):
        """Should raise GraphLoadError for missing file."""
        missing = tmp_path / "nonexistent.yaml"

        with pytest.raises(GraphLoadError) as exc_info:
            load_graph_config(missing)

        assert "not found" in str(exc_info.value)
        assert str(missing) in str(exc_info.value)

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_raises_on_invalid_yaml(self, tmp_path: Path):
        """Should raise GraphLoadError for invalid YAML."""
        graph_file = tmp_path / "invalid.yaml"
        graph_file.write_text("name: [invalid yaml")

        with pytest.raises(GraphLoadError) as exc_info:
            load_graph_config(graph_file)

        assert "Invalid YAML" in str(exc_info.value)

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_accepts_string_path(self, tmp_path: Path):
        """Should accept string paths as well as Path objects."""
        graph_file = tmp_path / "test.yaml"
        graph_file.write_text("name: test\nnodes: {}\nedges: []")

        config = load_graph_config(str(graph_file))

        assert config["name"] == "test"

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_returns_empty_dict_for_empty_yaml(self, tmp_path: Path):
        """Should return None/empty for empty YAML file."""
        graph_file = tmp_path / "empty.yaml"
        graph_file.write_text("")

        config = load_graph_config(graph_file)

        assert config is None


class TestRequireGraphConfig:
    """Test require_graph_config helper."""

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_returns_config_for_valid_yaml(self, tmp_path: Path):
        """Should return config dict for valid YAML."""
        graph_file = tmp_path / "test.yaml"
        graph_file.write_text("name: test\nnodes: {}\nedges: []")

        config = require_graph_config(graph_file)

        assert config["name"] == "test"

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_raises_on_empty_yaml(self, tmp_path: Path):
        """Should raise GraphLoadError for empty YAML file."""
        graph_file = tmp_path / "empty.yaml"
        graph_file.write_text("")

        with pytest.raises(GraphLoadError) as exc_info:
            require_graph_config(graph_file)

        assert "Empty YAML file" in str(exc_info.value)

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_raises_on_missing_file(self, tmp_path: Path):
        """Should raise GraphLoadError for missing file."""
        missing = tmp_path / "nonexistent.yaml"

        with pytest.raises(GraphLoadError) as exc_info:
            require_graph_config(missing)

        assert "not found" in str(exc_info.value)
