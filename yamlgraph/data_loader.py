"""Load external YAML data files into graph state.

This module provides the `data_files` directive functionality, loading
YAML files relative to the graph file at compile time.
"""

from pathlib import Path
from typing import Any

import yaml


class DataFileError(Exception):
    """Error loading a data file."""

    pass


def load_data_files(config: dict, graph_path: Path) -> dict[str, Any]:
    """Load external YAML files into initial state.

    Args:
        config: Graph configuration dict containing optional `data_files` key
        graph_path: Path to the graph YAML file

    Returns:
        Dict mapping state keys to loaded data

    Raises:
        DataFileError: If file not found, path escapes graph directory,
                       or value is not a string path

    Example:
        >>> config = {"data_files": {"schema": "schema.yaml"}}
        >>> data = load_data_files(config, Path("graphs/main.yaml"))
        >>> data["schema"]  # Contents of graphs/schema.yaml
    """
    data_files = config.get("data_files", {})
    if not data_files:
        return {}

    graph_dir = graph_path.parent.resolve()
    loaded: dict[str, Any] = {}

    for key, value in data_files.items():
        # Phase 1: Only string paths supported
        if not isinstance(value, str):
            raise DataFileError(
                f"data_files[{key}]: Expected string path, got {type(value).__name__}"
            )

        rel_path = value
        file_path = (graph_dir / rel_path).resolve()

        # Security: prevent path traversal
        try:
            file_path.relative_to(graph_dir)
        except ValueError:
            raise DataFileError(
                f"data_files[{key}]: Path '{rel_path}' escapes graph directory.\n"
                f"  Resolved: {file_path}\n"
                f"  Must be within: {graph_dir}"
            ) from None

        if not file_path.exists():
            raise DataFileError(
                f"data_files[{key}]: File not found\n"
                f"  Path: {file_path}\n"
                f"  Hint: Create the file or check the path in your graph YAML"
            )

        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise DataFileError(
                f"data_files[{key}]: Invalid YAML in '{rel_path}'\n  Error: {e}"
            ) from e

        # Empty files return None from safe_load; normalize to empty dict
        loaded[key] = data if data is not None else {}

    return loaded
