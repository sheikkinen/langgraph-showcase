"""Animated character storyboard node.

Workflow:
1. If no reference_image provided, generate character.png from character_prompt
2. For each panel:
   - Original: img2img from character/reference (magic=0.25 for consistency)
   - First frame: img2img from original
   - Last frame: img2img from original

This ensures character consistency across all panels.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .replicate_tool import edit_image, generate_image

logger = logging.getLogger(__name__)

GraphState = dict[str, Any]


def generate_animated_character_images(state: GraphState) -> dict:
    """Generate animated character-consistent storyboard images.

    Workflow:
    1. If no reference_image: generate character.png from character_prompt
    2. For each panel:
       - Original: img2img from character/reference
       - First frame: img2img from original
       - Last frame: img2img from original

    Args:
        state: Graph state with 'story', 'animated_panels', and optional 'reference_image'

    Returns:
        State update with 'images', 'character_image', 'output_dir'
    """
    story = state.get("story")
    animated_panels = state.get("animated_panels", [])

    if not story:
        logger.error("No story in state")
        return {
            "current_step": "generate_animated_character_images",
            "images": [],
            "error": "No story in state",
        }

    # Handle Pydantic model or dict
    if hasattr(story, "model_dump"):
        story_dict = story.model_dump()
    elif isinstance(story, dict):
        story_dict = story
    else:
        story_dict = {}

    character_prompt = story_dict.get("character_prompt", "")
    if not character_prompt:
        logger.error("No character_prompt in story")
        return {
            "current_step": "generate_animated_character_images",
            "images": [],
            "error": "No character_prompt provided",
        }

    if not animated_panels:
        logger.error("No animated_panels in state")
        return {
            "current_step": "generate_animated_character_images",
            "images": [],
            "error": "No animated panels to generate",
        }

    # Sort by _map_index if present
    if animated_panels and isinstance(animated_panels[0], dict):
        animated_panels = sorted(
            animated_panels,
            key=lambda x: x.get("_map_index", 0) if isinstance(x, dict) else 0,
        )

    # Create output directory
    thread_id = state.get("thread_id", datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_dir = Path("outputs/storyboard") / thread_id / "animated"
    output_dir.mkdir(parents=True, exist_ok=True)

    model_name = state.get("model", "z-image")
    reference_image = state.get("reference_image")
    reference_path = Path(reference_image) if reference_image else None

    logger.info(f"🎬 Generating animated character storyboard in {output_dir}")
    logger.info(f"🖼️  Using model: {model_name}")

    # If no reference provided, generate a character image first
    if not reference_path:
        character_path = output_dir / "character.png"
        logger.info("🎭 Generating character base image...")
        char_result = generate_image(
            prompt=character_prompt,
            output_path=character_path,
            model_name=model_name,
        )
        if char_result.success:
            reference_path = character_path
            logger.info(f"✓ Character image created: {character_path}")
        else:
            logger.error(f"Character generation failed: {char_result.error}")
            return {
                "current_step": "generate_animated_character_images",
                "images": [],
                "error": f"Character generation failed: {char_result.error}",
            }
    else:
        logger.info(f"🎭 Using reference image: {reference_path}")

    # Generate frames for each panel
    # Each panel: img2img from character/reference, then img2img for first/last
    total_images = len(animated_panels) * 3
    logger.info(
        f"🎞️  Generating {total_images} frames ({len(animated_panels)} panels × 3)"
    )

    all_results: list[dict] = []

    for panel_idx, panel in enumerate(animated_panels, 1):
        if hasattr(panel, "model_dump"):
            panel_dict = panel.model_dump()
        elif isinstance(panel, dict):
            panel_dict = panel
        else:
            logger.warning(f"Panel {panel_idx} has unexpected type: {type(panel)}")
            continue

        panel_result = {"panel": panel_idx, "frames": {}}

        # Step 1: Generate ORIGINAL image via img2img from character/reference
        original_prompt = panel_dict.get("original", "")
        if not original_prompt:
            logger.warning(f"Panel {panel_idx} missing original prompt")
            continue

        # Combine character + scene for consistency
        full_original_prompt = f"{character_prompt}, {original_prompt}"
        original_path = output_dir / f"panel_{panel_idx}_original.png"
        logger.info(f"📸 Panel {panel_idx} original: {original_prompt[:50]}...")

        # Use img2img from reference for character consistency
        # magic=0.25 preserves more of the reference (lower = more original)
        original_result = edit_image(
            input_image=reference_path,
            prompt=full_original_prompt,
            output_path=original_path,
            aspect_ratio="16:9",
            magic=0.25,
        )

        if not original_result.success:
            logger.error(f"Panel {panel_idx} original failed: {original_result.error}")
            continue

        panel_result["frames"]["original"] = str(original_path)
        logger.info(f"✓ Panel {panel_idx} original created")

        # Step 2: Generate first_frame via img2img from original
        first_prompt = panel_dict.get("first_frame", "")
        if first_prompt:
            first_path = output_dir / f"panel_{panel_idx}_first_frame.png"
            logger.info(f"📸 Panel {panel_idx} first_frame: {first_prompt[:50]}...")

            first_result = edit_image(
                input_image=original_path,
                prompt=first_prompt,
                output_path=first_path,
                aspect_ratio="16:9",
            )

            if first_result.success and first_result.path:
                panel_result["frames"]["first_frame"] = first_result.path
            else:
                logger.error(
                    f"Panel {panel_idx} first_frame failed: {first_result.error}"
                )
                panel_result["frames"]["first_frame"] = None

        # Step 3: Generate last_frame via img2img from original
        last_prompt = panel_dict.get("last_frame", "")
        if last_prompt:
            last_path = output_dir / f"panel_{panel_idx}_last_frame.png"
            logger.info(f"📸 Panel {panel_idx} last_frame: {last_prompt[:50]}...")

            last_result = edit_image(
                input_image=original_path,
                prompt=last_prompt,
                output_path=last_path,
                aspect_ratio="16:9",
            )

            if last_result.success and last_result.path:
                panel_result["frames"]["last_frame"] = last_result.path
            else:
                logger.error(
                    f"Panel {panel_idx} last_frame failed: {last_result.error}"
                )
                panel_result["frames"]["last_frame"] = None

        all_results.append(panel_result)

    # Save metadata
    frame_keys = ["first_frame", "original", "last_frame"]
    metadata_path = output_dir / "animated_character_story.json"
    metadata = {
        "concept": state.get("concept", ""),
        "title": story_dict.get("title", ""),
        "narrative": story_dict.get("narrative", ""),
        "character_prompt": character_prompt,
        "reference_image": str(reference_path) if reference_path else None,
        "panels": [
            {
                "index": r["panel"],
                "frames": r["frames"],
                "prompts": {
                    k: animated_panels[r["panel"] - 1].get(k, "")
                    if isinstance(animated_panels[r["panel"] - 1], dict)
                    else ""
                    for k in frame_keys
                },
            }
            for r in all_results
        ],
        "generated_at": datetime.now().isoformat(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))
    logger.info(f"📝 Metadata saved: {metadata_path}")

    success_count = sum(1 for r in all_results for path in r["frames"].values() if path)
    logger.info(f"✅ Generated {success_count}/{total_images} images")

    return {
        "current_step": "generate_animated_character_images",
        "character_image": str(reference_path),
        "images": all_results,
        "output_dir": str(output_dir),
    }
