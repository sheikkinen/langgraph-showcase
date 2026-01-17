"""Unified prompt loading and path resolution.

This module consolidates prompt loading logic used by executor.py
and node_factory.py into a single, testable module.

Search order for prompts:
1. {prompts_dir}/{prompt_name}.yaml (standard location)
2. {parent}/prompts/{basename}.yaml (external examples like examples/storyboard/...)
"""

from pathlib import Path

import yaml

from yamlgraph.config import PROMPTS_DIR


def resolve_prompt_path(
    prompt_name: str,
    prompts_dir: Path | None = None,
) -> Path:
    """Resolve a prompt name to its full YAML file path.

    Search order:
    1. prompts_dir/{prompt_name}.yaml (default: prompts/)
    2. {parent}/prompts/{basename}.yaml (for external examples)

    Args:
        prompt_name: Prompt name like "greet" or "examples/storyboard/expand_story"
        prompts_dir: Base prompts directory (defaults to PROMPTS_DIR from config)

    Returns:
        Path to the YAML file

    Raises:
        FileNotFoundError: If prompt file doesn't exist

    Examples:
        >>> resolve_prompt_path("greet")
        PosixPath('/path/to/prompts/greet.yaml')

        >>> resolve_prompt_path("map-demo/generate_ideas")
        PosixPath('/path/to/prompts/map-demo/generate_ideas.yaml')
    """
    if prompts_dir is None:
        prompts_dir = PROMPTS_DIR

    prompts_dir = Path(prompts_dir)

    # Try standard location first: prompts_dir/{prompt_name}.yaml
    yaml_path = prompts_dir / f"{prompt_name}.yaml"
    if yaml_path.exists():
        return yaml_path

    # Try external example location: {parent}/prompts/{basename}.yaml
    # e.g., "examples/storyboard/expand_story" -> "examples/storyboard/prompts/expand_story.yaml"
    parts = prompt_name.rsplit("/", 1)
    if len(parts) == 2:
        parent_dir, basename = parts
        alt_path = Path(parent_dir) / "prompts" / f"{basename}.yaml"
        if alt_path.exists():
            return alt_path

    raise FileNotFoundError(f"Prompt not found: {yaml_path}")


def load_prompt(
    prompt_name: str,
    prompts_dir: Path | None = None,
) -> dict:
    """Load a YAML prompt template.

    Args:
        prompt_name: Name of the prompt file (without .yaml extension)
        prompts_dir: Optional prompts directory override

    Returns:
        Dictionary with prompt content (typically 'system' and 'user' keys)

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    path = resolve_prompt_path(prompt_name, prompts_dir)

    with open(path) as f:
        return yaml.safe_load(f)


def load_prompt_path(
    prompt_name: str,
    prompts_dir: Path | None = None,
) -> tuple[Path, dict]:
    """Load a prompt and return both path and content.

    Useful when you need both the file path (for schema loading)
    and the content (for prompt execution).

    Args:
        prompt_name: Name of the prompt file (without .yaml extension)
        prompts_dir: Optional prompts directory override

    Returns:
        Tuple of (path, content_dict)

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    path = resolve_prompt_path(prompt_name, prompts_dir)

    with open(path) as f:
        content = yaml.safe_load(f)

    return path, content


__all__ = ["resolve_prompt_path", "load_prompt", "load_prompt_path"]
