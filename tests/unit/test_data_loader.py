"""Tests for data_loader module - TDD: Write tests first."""

import os
from pathlib import Path

import pytest

# Import will fail until we create the module
from yamlgraph.data_loader import DataFileError, load_data_files


class TestLoadDataFiles:
    """Test load_data_files function."""

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_empty_data_files_returns_empty_dict(self, tmp_path: Path) -> None:
        """No data_files directive returns empty dict."""
        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config: dict = {}
        result = load_data_files(config, graph_path)

        assert result == {}

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_load_single_yaml_file(self, tmp_path: Path) -> None:
        """Load a single YAML file into state."""
        # Create data file
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text("fields:\n  - name: age\n    type: int")

        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"schema": "schema.yaml"}}
        result = load_data_files(config, graph_path)

        assert result == {"schema": {"fields": [{"name": "age", "type": "int"}]}}

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_load_multiple_yaml_files(self, tmp_path: Path) -> None:
        """Load multiple YAML files."""
        # Create data files
        (tmp_path / "schema.yaml").write_text("version: 1")
        (tmp_path / "config.yaml").write_text("debug: true")

        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"schema": "schema.yaml", "config": "config.yaml"}}
        result = load_data_files(config, graph_path)

        assert result == {"schema": {"version": 1}, "config": {"debug": True}}

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_load_from_subdirectory(self, tmp_path: Path) -> None:
        """Load YAML file from subdirectory."""
        subdir = tmp_path / "data"
        subdir.mkdir()
        (subdir / "schema.yaml").write_text("name: test")

        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"schema": "data/schema.yaml"}}
        result = load_data_files(config, graph_path)

        assert result == {"schema": {"name": "test"}}


class TestDataFileErrors:
    """Test error handling."""

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_missing_file_raises_error(self, tmp_path: Path) -> None:
        """Missing data file raises DataFileError with clear message."""
        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"schema": "missing.yaml"}}

        with pytest.raises(DataFileError) as exc_info:
            load_data_files(config, graph_path)

        error_msg = str(exc_info.value)
        assert "data_files[schema]" in error_msg
        assert "File not found" in error_msg
        assert "missing.yaml" in error_msg
        assert "Hint:" in error_msg

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Path traversal attempts are blocked."""
        # Create a file outside graph directory
        parent = tmp_path.parent
        secret_file = parent / "secret.yaml"
        secret_file.write_text("password: 12345")

        graph_dir = tmp_path / "graphs"
        graph_dir.mkdir()
        graph_path = graph_dir / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"secret": "../secret.yaml"}}

        with pytest.raises(DataFileError) as exc_info:
            load_data_files(config, graph_path)

        error_msg = str(exc_info.value)
        assert "escapes graph directory" in error_msg
        assert "../secret.yaml" in error_msg

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_deep_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Deep path traversal (../../..) is blocked."""
        graph_dir = tmp_path / "a" / "b" / "c"
        graph_dir.mkdir(parents=True)
        graph_path = graph_dir / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"etc": "../../../etc/passwd"}}

        with pytest.raises(DataFileError) as exc_info:
            load_data_files(config, graph_path)

        assert "escapes graph directory" in str(exc_info.value)

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_symlink_traversal_blocked(self, tmp_path: Path) -> None:
        """Symlinks pointing outside graph directory are blocked."""
        # Create secret file outside
        secret_dir = tmp_path / "secrets"
        secret_dir.mkdir()
        secret_file = secret_dir / "creds.yaml"
        secret_file.write_text("api_key: secret123")

        # Create graph directory with symlink
        graph_dir = tmp_path / "graphs"
        graph_dir.mkdir()
        graph_path = graph_dir / "graph.yaml"
        graph_path.touch()

        # Create symlink pointing outside
        symlink = graph_dir / "creds.yaml"
        symlink.symlink_to(secret_file)

        config = {"data_files": {"creds": "creds.yaml"}}

        with pytest.raises(DataFileError) as exc_info:
            load_data_files(config, graph_path)

        assert "escapes graph directory" in str(exc_info.value)

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        """Empty YAML file returns empty dict, not None."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"data": "empty.yaml"}}
        result = load_data_files(config, graph_path)

        assert result == {"data": {}}
        assert result["data"] is not None

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Invalid YAML syntax raises clear error."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("key: [unclosed bracket")

        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"data": "bad.yaml"}}

        with pytest.raises(DataFileError, match="YAML"):
            load_data_files(config, graph_path)

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_non_string_path_raises_error(self, tmp_path: Path) -> None:
        """Non-string path value raises DataFileError."""
        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config = {
            "data_files": {"schema": {"path": "schema.yaml"}}
        }  # Extended syntax not supported

        with pytest.raises(DataFileError) as exc_info:
            load_data_files(config, graph_path)

        assert "Expected string path" in str(exc_info.value)


class TestPathResolution:
    """Test path resolution relative to graph file."""

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_path_relative_to_graph_not_cwd(self, tmp_path: Path) -> None:
        """Paths are resolved relative to graph file, not CWD."""
        # Create graph in subdirectory
        graph_dir = tmp_path / "project" / "graphs"
        graph_dir.mkdir(parents=True)
        graph_path = graph_dir / "graph.yaml"
        graph_path.touch()

        # Create data file next to graph
        data_file = graph_dir / "schema.yaml"
        data_file.write_text("version: 2")

        # Change CWD to different location
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            config = {"data_files": {"schema": "schema.yaml"}}
            result = load_data_files(config, graph_path)

            assert result == {"schema": {"version": 2}}
        finally:
            os.chdir(original_cwd)

    @pytest.mark.req("REQ-YG-001", "REQ-YG-004")
    def test_nested_subdirectory_works(self, tmp_path: Path) -> None:
        """Nested subdirectories work correctly."""
        # Create nested structure
        data_dir = tmp_path / "data" / "schemas" / "v1"
        data_dir.mkdir(parents=True)
        (data_dir / "main.yaml").write_text("id: 1")

        graph_path = tmp_path / "graph.yaml"
        graph_path.touch()

        config = {"data_files": {"schema": "data/schemas/v1/main.yaml"}}
        result = load_data_files(config, graph_path)

        assert result == {"schema": {"id": 1}}
