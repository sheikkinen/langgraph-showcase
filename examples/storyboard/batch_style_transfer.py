#!/usr/bin/env python3
"""Batch img2img style transfer.

Usage:
    python batch_style_transfer.py <input_dir> <output_dir> --style "your style prompt"
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from examples.shared.replicate_tool import edit_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Batch img2img style transfer")
    parser.add_argument("input_dir", type=Path, help="Input directory with images")
    parser.add_argument("output_dir", type=Path, help="Output directory for results")
    parser.add_argument(
        "--style",
        required=True,
        help="Style prompt to apply to all images",
    )
    parser.add_argument(
        "--magic",
        type=float,
        default=0.5,
        help="Prompt strength: 0=more original, 1=more prompt (default: 0.5)",
    )
    parser.add_argument(
        "--pattern",
        default="*.jpg",
        help="Glob pattern for input files (default: *.jpg)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without processing",
    )

    args = parser.parse_args()

    # Validate input directory
    if not args.input_dir.exists():
        logger.error(f"Input directory not found: {args.input_dir}")
        sys.exit(1)

    # Find images
    images = sorted(args.input_dir.glob(args.pattern))
    if not images:
        logger.error(f"No images matching {args.pattern} in {args.input_dir}")
        sys.exit(1)

    logger.info(f"Found {len(images)} images in {args.input_dir}")
    logger.info(f"Style: {args.style[:60]}...")
    logger.info(f"Magic: {args.magic}")

    # Setup output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output: {args.output_dir}")

    # Dry run
    if args.dry_run:
        logger.info("DRY RUN - would process:")
        for img in images[:5]:
            print(f"  {img.name} → {args.output_dir / img.stem}.png")
        if len(images) > 5:
            print(f"  ... and {len(images) - 5} more")
        return

    # Process images
    success = 0
    failed = 0

    for i, img_path in enumerate(images, 1):
        output_path = args.output_dir / f"{img_path.stem}.png"
        logger.info(f"[{i}/{len(images)}] {img_path.name}...")

        result = edit_image(
            input_image=img_path,
            prompt=args.style,
            output_path=output_path,
            magic=args.magic,
        )

        if result.success:
            success += 1
            logger.info(f"  ✓ {output_path.name}")
        else:
            failed += 1
            logger.error(f"  ✗ {result.error}")

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info(f"Done! {success}/{len(images)} images processed")
    if failed:
        logger.warning(f"  {failed} failed")
    logger.info(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
