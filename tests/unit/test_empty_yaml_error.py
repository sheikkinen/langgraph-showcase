"""Tests for empty YAML file error handling.

Bug: load_graph_config throws AttributeError on empty YAML files instead
of a clear ValueError, because yaml.safe_load returns None.
"""

import tempfile
from pathlib import Path

import pytest


class TestEmptyYamlHandling:
    """Tests for empty/invalid YAML file error handling."""

    def test_empty_yaml_throws_attributeerror(self) -> None:
        """Empty YAML file throws AttributeError instead of ValueError.

        Bug: yaml.safe_load returns None for empty files, and
        apply_loop_node_defaults calls config.get() which fails.
        """
        from yamlgraph.graph_loader import load_graph_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            tmpfile = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                load_graph_config(tmpfile)

            # Should give clear error about empty/invalid config
            error_message = str(exc_info.value).lower()
            assert (
                "empty" in error_message or "invalid" in error_message
            ), f"Error should mention empty/invalid config. Got: {exc_info.value}"
        finally:
            tmpfile.unlink()

    def test_yaml_with_only_comments_throws_valueerror(self) -> None:
        """YAML with only comments is effectively empty."""
        from yamlgraph.graph_loader import load_graph_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("# This is a comment\n# Another comment\n")
            tmpfile = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                load_graph_config(tmpfile)

            error_message = str(exc_info.value).lower()
            assert "empty" in error_message or "invalid" in error_message
        finally:
            tmpfile.unlink()

    def test_yaml_with_null_throws_valueerror(self) -> None:
        """YAML containing just 'null' should give clear error."""
        from yamlgraph.graph_loader import load_graph_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("null\n")
            tmpfile = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                load_graph_config(tmpfile)

            error_message = str(exc_info.value).lower()
            assert "empty" in error_message or "invalid" in error_message
        finally:
            tmpfile.unlink()
