"""Storyboard node for generating panel images.

This node takes story panels from the LLM and generates images via Replicate.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .replicate_tool import ImageResult, generate_image

logger = logging.getLogger(__name__)

# Type alias for state
GraphState = dict[str, Any]


def generate_images_node(state: GraphState) -> dict:
    """Generate images for each story panel.

    Reads panel prompts from state.story and generates images.
    Saves to outputs/storyboard/{thread_id}/ directory.

    Args:
        state: Graph state with 'story' containing panel prompts

    Returns:
        State update with 'images' list and metadata
    """
    story = state.get("story")
    if not story:
        logger.error("No story in state")
        return {
            "current_step": "generate_images",
            "images": [],
            "error": "No story panels to generate",
        }

    # Handle Pydantic model or dict
    if hasattr(story, "model_dump"):
        story_dict = story.model_dump()
    elif isinstance(story, dict):
        story_dict = story
    else:
        story_dict = {"panels": [str(story)]}

    # Extract panel prompts (supports dynamic list)
    panels = story_dict.get("panels", [])
    if not panels:
        # Fallback for legacy panel_1/2/3 format
        panels = [
            story_dict.get("panel_1", ""),
            story_dict.get("panel_2", ""),
            story_dict.get("panel_3", ""),
        ]
        panels = [p for p in panels if p]  # Remove empty

    # Create output directory
    thread_id = state.get("thread_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_dir = Path("outputs/storyboard") / thread_id
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"🎬 Generating {len(panels)}-panel storyboard in {output_dir}")

    # Get model selection from state (default: z-image)
    model_name = state.get("model", "z-image")
    logger.info(f"\ud83d\uddbc\ufe0f  Using model: {model_name}")

    # Generate each panel image
    results: list[ImageResult] = []
    image_paths: list[str] = []

    for i, prompt in enumerate(panels, 1):
        if not prompt:
            logger.warning(f"Panel {i} has no prompt, skipping")
            continue

        output_path = output_dir / f"panel_{i}.png"
        logger.info(f"\ud83d\udcf8 Panel {i}: {prompt[:60]}...")

        result = generate_image(prompt, output_path, model_name=model_name)
        results.append(result)

        if result.success and result.path:
            image_paths.append(result.path)
        else:
            logger.error(f"Panel {i} failed: {result.error}")

    # Save story metadata
    metadata_path = output_dir / "story.json"
    metadata = {
        "concept": state.get("concept", ""),
        "title": story_dict.get("title", ""),
        "narrative": story_dict.get("narrative", ""),
        "panels": [
            {
                "prompt": panels[i] if i < len(panels) else "",
                "image": image_paths[i] if i < len(image_paths) else None,
            }
            for i in range(max(len(panels), len(image_paths)))
        ],
        "generated_at": datetime.now().isoformat(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))
    logger.info(f"📝 Metadata saved: {metadata_path}")

    success_count = sum(1 for r in results if r.success)
    logger.info(f"✅ Generated {success_count}/{len(panels)} images")

    return {
        "current_step": "generate_images",
        "images": image_paths,
        "output_dir": str(output_dir),
    }
