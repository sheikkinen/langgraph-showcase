"""Unified prompt loading and path resolution.

This module consolidates prompt loading logic used by executor.py
and node_factory.py into a single, testable module.

Search order for prompts:
1. If prompts_relative + prompts_dir + graph_path: graph_path.parent/prompts_dir/{prompt_name}.yaml
2. If prompts_dir specified: prompts_dir/{prompt_name}.yaml
3. If prompts_relative + graph_path: graph_path.parent/{prompt_name}.yaml
4. Default: PROMPTS_DIR/{prompt_name}.yaml
5. Fallback: {parent}/prompts/{basename}.yaml (external examples)
"""

import logging
from pathlib import Path

import yaml

from yamlgraph.config import PROMPTS_DIR

logger = logging.getLogger(__name__)


def resolve_prompt_path(
    prompt_name: str,
    prompts_dir: Path | None = None,
    graph_path: Path | None = None,
    prompts_relative: bool = False,
) -> Path:
    """Resolve a prompt name to its full YAML file path.

    Resolution order:
    1. If prompts_relative + prompts_dir + graph_path: graph_path.parent/prompts_dir/{prompt_name}.yaml
    2. If prompts_dir specified: prompts_dir/{prompt_name}.yaml
    3. If prompts_relative + graph_path: graph_path.parent/{prompt_name}.yaml
    4. Default: PROMPTS_DIR/{prompt_name}.yaml
    5. Fallback: {parent}/prompts/{basename}.yaml (external examples)

    Args:
        prompt_name: Prompt name like "greet" or "prompts/opening"
        prompts_dir: Explicit prompts directory (combined with graph_path if prompts_relative=True)
        graph_path: Path to the graph YAML file (for relative resolution)
        prompts_relative: If True, resolve relative to graph_path.parent

    Returns:
        Path to the YAML file

    Raises:
        FileNotFoundError: If prompt file doesn't exist
        ValueError: If prompts_relative=True but graph_path not provided

    Examples:
        >>> resolve_prompt_path("greet")
        PosixPath('/path/to/prompts/greet.yaml')

        >>> resolve_prompt_path("prompts/opening", graph_path=Path("graphs/demo.yaml"), prompts_relative=True)
        PosixPath('/path/to/graphs/prompts/opening.yaml')

        >>> resolve_prompt_path("opening", prompts_dir="prompts", graph_path=Path("graphs/demo.yaml"), prompts_relative=True)
        PosixPath('/path/to/graphs/prompts/opening.yaml')
    """
    # Validate prompts_relative requires graph_path
    if prompts_relative and graph_path is None and prompts_dir is None:
        raise ValueError("graph_path required when prompts_relative=True")

    tried_paths: list[str] = []  # Track for debug logging

    # 1. Graph-relative with explicit prompts_dir (combine them)
    if prompts_relative and prompts_dir is not None and graph_path is not None:
        graph_dir = Path(graph_path).parent
        yaml_path = graph_dir / prompts_dir / f"{prompt_name}.yaml"
        tried_paths.append(f"1:graph-relative+prompts_dir:{yaml_path}")
        if yaml_path.exists():
            logger.debug(f"Prompt resolved via graph-relative+prompts_dir: {yaml_path}")
            return yaml_path
        # Fall through if not found

    # 2. Explicit prompts_dir (absolute path or CWD-relative)
    if prompts_dir is not None:
        prompts_dir = Path(prompts_dir)
        yaml_path = prompts_dir / f"{prompt_name}.yaml"
        tried_paths.append(f"2:explicit_prompts_dir:{yaml_path}")
        if yaml_path.exists():
            logger.debug(f"Prompt resolved via explicit prompts_dir: {yaml_path}")
            return yaml_path
        # Fall through to other resolution methods

    # 3. Graph-relative resolution (without explicit prompts_dir)
    if prompts_relative and graph_path is not None:
        graph_dir = Path(graph_path).parent
        yaml_path = graph_dir / f"{prompt_name}.yaml"
        tried_paths.append(f"3:graph-relative:{yaml_path}")
        if yaml_path.exists():
            logger.debug(f"Prompt resolved via graph-relative: {yaml_path}")
            return yaml_path
        # Fall through to default

    # 4. Default: use global PROMPTS_DIR
    default_dir = PROMPTS_DIR if prompts_dir is None else prompts_dir
    yaml_path = Path(default_dir) / f"{prompt_name}.yaml"
    tried_paths.append(f"4:default_PROMPTS_DIR:{yaml_path}")
    if yaml_path.exists():
        logger.debug(f"Prompt resolved via default PROMPTS_DIR: {yaml_path}")
        return yaml_path

    # 5. Fallback: external example location {parent}/prompts/{basename}.yaml
    parts = prompt_name.rsplit("/", 1)
    if len(parts) == 2:
        parent_dir, basename = parts
        alt_path = Path(parent_dir) / "prompts" / f"{basename}.yaml"
        tried_paths.append(f"5:external_fallback:{alt_path}")
        if alt_path.exists():
            logger.debug(f"Prompt resolved via external fallback: {alt_path}")
            return alt_path

    # Log all tried paths for debugging
    logger.debug(f"Prompt '{prompt_name}' not found. Tried: {tried_paths}")
    raise FileNotFoundError(f"Prompt not found: {yaml_path}")


def load_prompt(
    prompt_name: str,
    prompts_dir: Path | None = None,
    graph_path: Path | None = None,
    prompts_relative: bool = False,
) -> dict:
    """Load a YAML prompt template.

    Args:
        prompt_name: Name of the prompt file (without .yaml extension)
        prompts_dir: Optional prompts directory override
        graph_path: Path to the graph YAML file (for relative resolution)
        prompts_relative: If True, resolve relative to graph_path.parent

    Returns:
        Dictionary with prompt content (typically 'system' and 'user' keys)

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    path = resolve_prompt_path(
        prompt_name,
        prompts_dir=prompts_dir,
        graph_path=graph_path,
        prompts_relative=prompts_relative,
    )

    with open(path) as f:
        return yaml.safe_load(f)


def load_prompt_path(
    prompt_name: str,
    prompts_dir: Path | None = None,
    graph_path: Path | None = None,
    prompts_relative: bool = False,
) -> tuple[Path, dict]:
    """Load a prompt and return both path and content.

    Useful when you need both the file path (for schema loading)
    and the content (for prompt execution).

    Args:
        prompt_name: Name of the prompt file (without .yaml extension)
        prompts_dir: Optional prompts directory override
        graph_path: Path to the graph YAML file (for relative resolution)
        prompts_relative: If True, resolve relative to graph_path.parent

    Returns:
        Tuple of (path, content_dict)

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    path = resolve_prompt_path(
        prompt_name,
        prompts_dir=prompts_dir,
        graph_path=graph_path,
        prompts_relative=prompts_relative,
    )

    with open(path) as f:
        content = yaml.safe_load(f)

    return path, content


__all__ = ["resolve_prompt_path", "load_prompt", "load_prompt_path"]
