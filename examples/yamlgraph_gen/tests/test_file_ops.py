"""Tests for file_ops module."""

from pathlib import Path

import pytest

from examples.yamlgraph_gen.tools.file_ops import (
    ensure_directory,
    list_files,
    read_file,
    write_file,
    write_generated_files,
)


class TestReadFile:
    """Tests for read_file function."""

    def test_read_existing_file(self, tmp_path: Path) -> None:
        """Read contents of an existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        result = read_file(str(test_file))

        assert result == "hello world"

    def test_read_missing_file_raises(self, tmp_path: Path) -> None:
        """Reading missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            read_file(str(tmp_path / "missing.txt"))


class TestWriteFile:
    """Tests for write_file function."""

    def test_write_file(self, tmp_path: Path) -> None:
        """Write content to a file."""
        test_file = tmp_path / "output.txt"

        result = write_file(str(test_file), "test content")

        assert test_file.read_text() == "test content"
        assert result["bytes"] == 12

    def test_write_creates_directories(self, tmp_path: Path) -> None:
        """Write creates parent directories if needed."""
        test_file = tmp_path / "nested" / "dir" / "output.txt"

        write_file(str(test_file), "content")

        assert test_file.exists()
        assert test_file.read_text() == "content"


class TestListFiles:
    """Tests for list_files function."""

    def test_list_files_with_pattern(self, tmp_path: Path) -> None:
        """List files matching a pattern."""
        (tmp_path / "a.yaml").touch()
        (tmp_path / "b.yaml").touch()
        (tmp_path / "c.txt").touch()

        result = list_files(str(tmp_path), "*.yaml")

        assert len(result) == 2
        assert any("a.yaml" in f for f in result)
        assert any("b.yaml" in f for f in result)

    def test_list_files_empty_directory(self, tmp_path: Path) -> None:
        """List files in empty directory returns empty list."""
        result = list_files(str(tmp_path), "*.yaml")

        assert result == []


class TestEnsureDirectory:
    """Tests for ensure_directory function."""

    def test_ensure_directory_creates(self, tmp_path: Path) -> None:
        """Creates directory if it doesn't exist."""
        new_dir = tmp_path / "new_dir"

        ensure_directory(str(new_dir))

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_nested(self, tmp_path: Path) -> None:
        """Creates nested directories."""
        nested = tmp_path / "a" / "b" / "c"

        ensure_directory(str(nested))

        assert nested.exists()


class TestWriteGeneratedFiles:
    """Tests for write_generated_files function."""

    def test_write_graph_and_prompts(self, tmp_path: Path) -> None:
        """Write graph.yaml and prompt files."""
        graph_content = "version: '1.0'\nname: test"
        prompts = [
            {"filename": "node1.yaml", "content": "system: test1"},
            {"filename": "prompts/node2.yaml", "content": "system: test2"},
        ]

        result = write_generated_files(str(tmp_path), graph_content, prompts)

        assert result["status"] == "success"
        assert len(result["files_written"]) == 3
        assert (tmp_path / "graph.yaml").read_text() == graph_content
        assert (tmp_path / "prompts" / "node1.yaml").read_text() == "system: test1"
        assert (tmp_path / "prompts" / "node2.yaml").read_text() == "system: test2"

    def test_write_empty_prompts(self, tmp_path: Path) -> None:
        """Write just graph.yaml when no prompts."""
        result = write_generated_files(str(tmp_path), "version: '1.0'", [])

        assert result["status"] == "success"
        assert len(result["files_written"]) == 1
