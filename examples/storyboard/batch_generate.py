#!/usr/bin/env python3
"""Batch image generation from a prompts file.

Usage:
    python examples/storyboard/batch_generate.py prompts.txt
    python examples/storyboard/batch_generate.py prompts.txt --model hidream
    python examples/storyboard/batch_generate.py prompts.txt --output-dir outputs/batch

    # With reference image (img2img using p-image-edit)
    python examples/storyboard/batch_generate.py prompts.txt --reference character.png
    python examples/storyboard/batch_generate.py prompts.txt --reference character.png --magic 0.5

Input file format: one prompt per line (blank lines and #comments ignored)
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from examples.shared.replicate_tool import edit_image, generate_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_prompts(filepath: Path) -> list[str]:
    """Load prompts from file, one per line.

    Ignores blank lines and lines starting with #.
    """
    prompts = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                prompts.append(line)
    return prompts


def main():
    parser = argparse.ArgumentParser(
        description="Generate images from a prompts file (one prompt per line)"
    )
    parser.add_argument(
        "prompts_file", type=Path, help="File with prompts (one per line)"
    )
    parser.add_argument(
        "--model",
        choices=["z-image", "hidream"],
        default="hidream",
        help="Model to use (default: hidream)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: outputs/batch/<timestamp>)",
    )
    parser.add_argument(
        "--prefix",
        default="image",
        help="Filename prefix (default: image)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show prompts without generating",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="Reference image for img2img (uses p-image-edit model)",
    )
    parser.add_argument(
        "--magic",
        type=float,
        default=0.5,
        help="Prompt strength for img2img: 0=more original, 1=more prompt (default: 0.5)",
    )

    args = parser.parse_args()

    # Validate input file
    if not args.prompts_file.exists():
        logger.error(f"Prompts file not found: {args.prompts_file}")
        sys.exit(1)

    # Validate reference image if provided
    if args.reference and not args.reference.exists():
        logger.error(f"Reference image not found: {args.reference}")
        sys.exit(1)

    # Load prompts
    prompts = load_prompts(args.prompts_file)
    if not prompts:
        logger.error("No prompts found in file")
        sys.exit(1)

    logger.info(f"Loaded {len(prompts)} prompts from {args.prompts_file}")
    if args.reference:
        logger.info(f"Using reference image: {args.reference} (magic={args.magic})")

    # Setup output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("outputs/batch") / timestamp

    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Dry run - just show prompts
    if args.dry_run:
        mode = (
            "img2img (p-image-edit)" if args.reference else f"text2img ({args.model})"
        )
        logger.info(f"DRY RUN - would generate with {mode}:")
        for i, prompt in enumerate(prompts, 1):
            print(f"  {i}. {args.prefix}_{i:03d}.png: {prompt[:80]}...")
        return

    # Generate images
    mode = "p-image-edit" if args.reference else args.model
    logger.info(f"🎨 Generating {len(prompts)} images with {mode}...")
    success = 0
    failed = 0

    for i, prompt in enumerate(prompts, 1):
        output_path = output_dir / f"{args.prefix}_{i:03d}.png"
        logger.info(f"[{i}/{len(prompts)}] {prompt[:60]}...")

        if args.reference:
            # img2img mode
            result = edit_image(
                input_image=args.reference,
                prompt=prompt,
                output_path=output_path,
                magic=args.magic,
            )
        else:
            # text2img mode
            result = generate_image(
                prompt=prompt,
                output_path=output_path,
                model_name=args.model,
            )

        if result.success:
            success += 1
            logger.info(f"  ✓ {output_path}")
        else:
            failed += 1
            logger.error(f"  ✗ {result.error}")

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"Done! {success}/{len(prompts)} images generated")
    if failed:
        logger.warning(f"  {failed} failed")
    logger.info(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
