#!/usr/bin/env python3
"""Generate video clips from consecutive image pairs.

Takes a folder of images, sorts alphabetically, and generates
video clips for each consecutive pair (1→2, 2→3, 3→4, etc.)

Usage:
    python examples/storyboard/generate_videos.py outputs/storyboard/20260117_112419/animated

Options:
    --pattern GLOB     File pattern to match (default: *.png)
    --prompt TEXT      Prompt for video generation
    --fps INT          Frames per second (default: 16)
    --frames INT       Number of frames (default: 81)
    --resolution STR   Resolution: 480p, 720p (default: 480p)
    --dry-run          Show what would be generated without running
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Check if replicate is available
try:
    import replicate

    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False


def generate_video_clip(
    first_image: Path,
    last_image: Path,
    output_path: Path,
    prompt: str = "",
    fps: int = 16,
    num_frames: int = 81,
    resolution: str = "480p",
) -> bool:
    """Generate a video clip between two images.

    Args:
        first_image: Starting frame
        last_image: Ending frame
        output_path: Where to save the video
        prompt: Optional prompt describing the motion
        fps: Frames per second
        num_frames: Total number of frames
        resolution: Output resolution (480p, 720p)

    Returns:
        True if successful
    """
    if not REPLICATE_AVAILABLE:
        logger.error("replicate package not installed. Run: pip install replicate")
        return False

    api_token = os.environ.get("REPLICATE_API_TOKEN")
    if not api_token:
        logger.error("REPLICATE_API_TOKEN not set")
        return False

    try:
        logger.info(f"🎬 Generating: {first_image.name} → {last_image.name}")

        client = replicate.Client(api_token=api_token)

        with open(first_image, "rb") as f1, open(last_image, "rb") as f2:
            output = client.run(
                "wan-video/wan-2.2-i2v-fast",
                input={
                    "image": f1,
                    "last_image": f2,
                    "prompt": prompt or "Smooth camera motion, cinematic transition",
                    "go_fast": True,
                    "num_frames": num_frames,
                    "resolution": resolution,
                    "sample_shift": 12,
                    "frames_per_second": fps,
                    "interpolate_output": False,
                    "lora_scale_transformer": 1,
                    "lora_scale_transformer_2": 1,
                },
            )

        # Save the video
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(output.read())

        logger.info(f"✓ Saved: {output_path}")
        return True

    except Exception as e:
        logger.error(f"✗ Failed: {e}")
        return False


def get_prompt_for_pair(
    metadata: dict | None,
    img1_name: str,
    img2_name: str,
) -> str:
    """Try to extract relevant prompt from metadata."""
    if not metadata:
        return ""

    # Parse panel number from filename
    # e.g., "panel_1_first_frame.png" → panel 1
    for panel in metadata.get("panels", []):
        prompts = panel.get("prompts", {})

        # If transitioning within same panel, use the prompts
        if f"panel_{panel['index']}" in img1_name:
            if "first_frame" in img1_name and "original" in img2_name:
                return prompts.get("original", "")
            if "original" in img1_name and "last_frame" in img2_name:
                return prompts.get("last_frame", "")
            if "first_frame" in img1_name and "last_frame" in img2_name:
                return prompts.get("last_frame", "")

    return ""


def concatenate_videos(video_paths: list[Path], output_path: Path) -> bool:
    """Concatenate multiple video clips into one using ffmpeg.

    Args:
        video_paths: List of video files in order
        output_path: Output file path

    Returns:
        True if successful
    """
    if not video_paths:
        return False

    # Create concat file list in the same directory
    concat_file = output_path.parent / "concat_list.txt"
    with open(concat_file, "w") as f:
        for video in video_paths:
            f.write(f"file '{video.name}'\n")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",  # Overwrite
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                "concat_list.txt",  # Use relative name since cwd is set
                "-c",
                "copy",
                output_path.name,  # Use relative name
            ],
            capture_output=True,
            text=True,
            cwd=str(output_path.parent),  # Ensure string path
        )

        concat_file.unlink()  # Clean up

        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            return False

        return True

    except FileNotFoundError:
        logger.error("ffmpeg not found. Install with: brew install ffmpeg")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate video clips from consecutive image pairs"
    )
    parser.add_argument(
        "folder",
        type=Path,
        help="Folder containing images",
    )
    parser.add_argument(
        "--pattern",
        default="*.png",
        help="Glob pattern for images (default: *.png)",
    )
    parser.add_argument(
        "--prompt",
        default="",
        help="Prompt for all video generations",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=16,
        help="Frames per second (default: 16)",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=81,
        help="Number of frames (default: 81)",
    )
    parser.add_argument(
        "--resolution",
        default="480p",
        choices=["480p", "720p"],
        help="Output resolution (default: 480p)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without running",
    )
    args = parser.parse_args()

    folder = args.folder
    if not folder.exists():
        logger.error(f"❌ Folder not found: {folder}")
        sys.exit(1)

    # Find images (alphabetically sorted)
    images = sorted(folder.glob(args.pattern))
    if not images:
        logger.error(f"❌ No images matching '{args.pattern}' in {folder}")
        sys.exit(1)

    # Filter out non-frame images
    images = [img for img in images if img.name not in ("character.png",)]

    logger.info(f"📁 Found {len(images)} images in {folder} (alphabetical order)")
    for img in images:
        logger.info(f"   {img.name}")

    # Load metadata if available
    metadata_path = folder / "animated_character_story.json"
    metadata = None
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text())
        logger.info(f"📝 Loaded metadata from {metadata_path.name}")

    # Create output folder
    videos_folder = folder / "videos"
    if not args.dry_run:
        videos_folder.mkdir(exist_ok=True)

    # Generate videos for consecutive pairs
    pairs = list(zip(images[:-1], images[1:], strict=False))
    logger.info(f"\n🎬 Generating {len(pairs)} video clips (parallel):")

    # Build list of jobs
    jobs = []
    for i, (img1, img2) in enumerate(pairs, 1):
        output_name = f"clip_{i:02d}_{img1.stem}_to_{img2.stem}.mp4"
        output_path = videos_folder / output_name
        prompt = args.prompt or get_prompt_for_pair(metadata, img1.name, img2.name)

        logger.info(f"   [{i}] {img1.name} → {img2.name}")
        if prompt:
            logger.info(f"       Prompt: {prompt[:50]}...")

        jobs.append(
            {
                "index": i,
                "img1": img1,
                "img2": img2,
                "output_path": output_path,
                "prompt": prompt,
            }
        )

    if args.dry_run:
        for job in jobs:
            logger.info(f"   Would save: {job['output_path']}")
        sys.exit(0)

    # Parallel generation
    generated_clips = []

    def run_job(job):
        success = generate_video_clip(
            first_image=job["img1"],
            last_image=job["img2"],
            output_path=job["output_path"],
            prompt=job["prompt"],
            fps=args.fps,
            num_frames=args.frames,
            resolution=args.resolution,
        )
        return job["index"], job["output_path"], success

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_job, job): job for job in jobs}

        for future in as_completed(futures):
            idx, output_path, success = future.result()
            if success:
                generated_clips.append((idx, output_path))

    # Sort by index and collect paths
    generated_clips.sort(key=lambda x: x[0])
    clip_paths = [path for _, path in generated_clips]

    logger.info(f"\n✅ Generated {len(clip_paths)}/{len(pairs)} video clips")

    # Concatenate into final video
    if len(clip_paths) > 1:
        final_output = videos_folder / "final_combined.mp4"
        logger.info(f"\n🎞️  Concatenating clips into {final_output.name}...")

        if concatenate_videos(clip_paths, final_output):
            logger.info(f"✅ Final video: {final_output}")
        else:
            logger.warning("⚠️  Concatenation failed, individual clips available")

    logger.info(f"📂 Output: {videos_folder}")


if __name__ == "__main__":
    main()
