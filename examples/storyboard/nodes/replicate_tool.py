"""Storyboard-specific wrappers for image generation.

Re-exports from examples.shared.replicate_tool and adds storyboard-specific functions.
"""

from __future__ import annotations

from pathlib import Path

from examples.shared.replicate_tool import (
    ImageResult,
    edit_image,
    generate_image,
)

# Re-export for backward compatibility
__all__ = [
    "ImageResult",
    "generate_image",
    "edit_image",
    "generate_storyboard_images",
]


def generate_storyboard_images(
    panel_prompts: list[str],
    output_dir: str | Path,
    prefix: str = "panel",
) -> list[ImageResult]:
    """Generate multiple images for a storyboard.

    Args:
        panel_prompts: List of prompts for each panel
        output_dir: Directory to save images
        prefix: Filename prefix

    Returns:
        List of ImageResult for each panel
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, prompt in enumerate(panel_prompts, 1):
        output_path = output_dir / f"{prefix}_{i}.png"
        result = generate_image(prompt, output_path)
        results.append(result)

    return results
