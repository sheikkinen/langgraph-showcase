"""Replicate image generation tool for storyboard workflow.

Supports multiple models:
- z-image: Fast, good for realistic/photographic (default)
- hidream: Better for cartoons, illustrations, stylized art
- p-image-edit: Image-to-image editing for character consistency
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Model configurations
MODELS = {
    "z-image": {
        "id": "prunaai/z-image-turbo",
        "width": 1344,
        "height": 768,
        "params": {
            "guidance_scale": 0,
            "num_inference_steps": 8,
        },
    },
    "hidream": {
        "id": "prunaai/hidream-l1-fast:f67f0ec7ef9fe91b74e8a68d34efaa9145bec28675cb190cbff8a70f0490256e",
        "resolution": "1360 \u00d7 768 (Landscape)",
        "params": {
            "model_type": "fast",
            "speed_mode": "Juiced \U0001f525 (more speed)",
        },
    },
}

DEFAULT_MODEL = "z-image"

# Check if replicate is available
try:
    import replicate

    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    logger.warning("replicate package not installed. Run: pip install replicate")


@dataclass
class ImageResult:
    """Result from image generation."""

    success: bool
    path: str | None = None
    error: str | None = None


def generate_image(
    prompt: str,
    output_path: str | Path,
    model_name: str = DEFAULT_MODEL,
) -> ImageResult:
    """Generate an image using Replicate API.

    Args:
        prompt: Text prompt for image generation
        output_path: Path to save the generated image
        model_name: Model to use ('z-image' or 'hidream')

    Returns:
        ImageResult with success status and path or error
    """
    if not REPLICATE_AVAILABLE:
        return ImageResult(success=False, error="replicate package not installed")

    api_token = os.environ.get("REPLICATE_API_TOKEN")
    if not api_token:
        return ImageResult(
            success=False, error="REPLICATE_API_TOKEN not set in environment"
        )

    # Get model config
    model_config = MODELS.get(model_name, MODELS[DEFAULT_MODEL])
    model_id = model_config["id"]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"🎨 Generating image with {model_name}: {prompt[:50]}...")

        # Build input params based on model
        if model_name == "hidream":
            input_params = {
                "prompt": prompt,
                "seed": -1,
                "resolution": model_config["resolution"],
                "output_format": "png",
                "output_quality": 80,
                "disable_safety_checker": True,
                **model_config["params"],
            }
        else:
            # z-image and default
            input_params = {
                "prompt": prompt,
                "width": model_config.get("width", 1344),
                "height": model_config.get("height", 768),
                "output_format": "png",
                "output_quality": 80,
                "disable_safety_checker": True,
                **model_config.get("params", {}),
            }

        # Run the model
        client = replicate.Client(api_token=api_token)
        output = client.run(model_id, input=input_params)

        # output is typically a URL or file-like object
        image_url = output if isinstance(output, str) else str(output)

        # Download the image
        logger.info(f"📥 Downloading image to {output_path}")
        response = httpx.get(image_url, timeout=60.0)
        response.raise_for_status()

        output_path.write_bytes(response.content)
        logger.info(f"✓ Image saved: {output_path}")

        return ImageResult(success=True, path=str(output_path))

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return ImageResult(success=False, error=str(e))


def edit_image(
    input_image: str | Path,
    prompt: str,
    output_path: str | Path,
    aspect_ratio: str = "16:9",
    turbo: bool = True,
    magic: float | None = None,
) -> ImageResult:
    """Edit an image using Replicate p-image-edit model.

    Uses the input image as base and applies the prompt as modifications.
    Great for maintaining character consistency across panels.

    Args:
        input_image: Path to the source image
        prompt: Edit instructions (what to change/add)
        output_path: Path to save the edited image
        aspect_ratio: Output aspect ratio (default 16:9)
        turbo: Use turbo mode for faster generation
        magic: Prompt strength 0-1 (lower = more original, higher = more prompt)

    Returns:
        ImageResult with success status and path or error
    """
    if not REPLICATE_AVAILABLE:
        return ImageResult(success=False, error="replicate package not installed")

    api_token = os.environ.get("REPLICATE_API_TOKEN")
    if not api_token:
        return ImageResult(
            success=False, error="REPLICATE_API_TOKEN not set in environment"
        )

    input_image = Path(input_image)
    if not input_image.exists():
        return ImageResult(success=False, error=f"Input image not found: {input_image}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"✏️ Editing image: {prompt[:50]}...")

        client = replicate.Client(api_token=api_token)

        with open(input_image, "rb") as f:
            input_params = {
                "turbo": turbo,
                "images": [f],
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "disable_safety_checker": True,
            }
            if magic is not None:
                input_params["magic"] = magic

            output = client.run(
                "prunaai/p-image-edit",
                input=input_params,
            )

        # Save the output
        with open(output_path, "wb") as out:
            out.write(output.read())

        logger.info(f"✓ Edited image saved: {output_path}")
        return ImageResult(success=True, path=str(output_path))

    except Exception as e:
        logger.error(f"Image editing failed: {e}")
        return ImageResult(success=False, error=str(e))


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
