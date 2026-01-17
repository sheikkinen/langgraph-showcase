#!/usr/bin/env python3
"""Retry image generation from existing animated storyboard metadata.

Usage:
    python examples/storyboard/retry_images.py outputs/storyboard/20260117_112419/animated

Options:
    --model MODEL         Image model to use (default: hidream)
    --reference PATH      Override reference image path
    --magic FLOAT         Magic value for img2img (default: 0.25)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from examples.storyboard.nodes.animated_character_node import (
    generate_animated_character_images,
)


def main():
    parser = argparse.ArgumentParser(
        description="Retry image generation from existing metadata"
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Path to animated output directory (contains animated_character_story.json)",
    )
    parser.add_argument(
        "--model",
        default="hidream",
        help="Image model to use (default: hidream)",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        help="Override reference image path",
    )
    parser.add_argument(
        "--new-id",
        help="New thread ID for output (default: adds _retry suffix)",
    )
    args = parser.parse_args()

    # Find metadata file
    output_dir = args.output_dir
    if output_dir.name != "animated":
        output_dir = output_dir / "animated"

    metadata_path = output_dir / "animated_character_story.json"
    if not metadata_path.exists():
        print(f"❌ Metadata not found: {metadata_path}")
        sys.exit(1)

    print(f"📂 Loading: {metadata_path}")
    metadata = json.loads(metadata_path.read_text())

    # Reconstruct animated_panels from metadata
    animated_panels = []
    for panel in metadata["panels"]:
        animated_panels.append(
            {
                "_map_index": panel["index"] - 1,
                **panel["prompts"],
            }
        )

    # Determine thread_id
    original_thread = output_dir.parent.name
    thread_id = args.new_id or f"{original_thread}_retry"

    # Build state
    state = {
        "concept": metadata["concept"],
        "model": args.model,
        "thread_id": thread_id,
        "story": {
            "title": metadata["title"],
            "narrative": metadata["narrative"],
            "character_prompt": metadata["character_prompt"],
        },
        "animated_panels": animated_panels,
    }

    # Handle reference image
    if args.reference:
        state["reference_image"] = str(args.reference)
    elif metadata.get("reference_image"):
        ref_path = Path(metadata["reference_image"])
        if ref_path.exists():
            state["reference_image"] = str(ref_path)
            print(f"🎭 Using existing reference: {ref_path}")

    print("🎬 Retrying image generation...")
    print(f"   Model: {args.model}")
    print(f"   Panels: {len(animated_panels)}")
    print(f"   Output: outputs/storyboard/{thread_id}/animated/")

    # Run image generation
    result = generate_animated_character_images(state)

    if result.get("error"):
        print(f"❌ Error: {result['error']}")
        sys.exit(1)

    print(f"\n✅ Generated images in: {result['output_dir']}")


if __name__ == "__main__":
    main()
