# Storyboard Generator

Generates a visual story with 3-5 panels from a concept using LLM + Replicate image generation.

## Usage

```bash
# Default (z-image model - photorealistic)
yamlgraph graph run examples/storyboard/graph.yaml \
  --var concept="A wizard's apprentice discovers a hidden library"

# HiDream model (cartoon/illustration style)
yamlgraph graph run examples/storyboard/graph.yaml \
  --var concept="A robot learning to paint" \
  --var model="hidream"
```

## Models

| Model | Style | Best For |
|-------|-------|----------|
| `z-image` (default) | Photorealistic, cinematic | Realistic scenes, photography |
| `hidream` | Cartoon, illustration | Stylized art, comics, anime |

The LLM automatically adapts prompts based on the selected model.

## How It Works

```
concept ──► expand_story (LLM) ──► generate_images (Python) ──► outputs/
```

1. **expand_story** - LLM expands concept into title, narrative, and 3-5 panel prompts
2. **generate_images** - Calls Replicate API to generate images for each panel

## Output

Results are saved to `outputs/storyboard/{timestamp}/`:

```
outputs/storyboard/20260117_120000/
├── panel_1.png
├── panel_2.png
├── panel_3.png
├── panel_4.png   # if LLM generated 4+ panels
└── story.json    # metadata with prompts and paths
```

## Requirements

- `REPLICATE_API_TOKEN` in `.env`

## Files

| File | Purpose |
|------|---------|
| `graph.yaml` | Graph definition |
| `prompts/expand_story.yaml` | LLM prompt with schema |
| `nodes/image_node.py` | Python node for image generation |
| `nodes/replicate_tool.py` | Replicate API wrapper |

---

## Animated Storyboard

Generates animation-ready storyboards with 3 frames per panel (original, first_frame, last_frame).

### Usage

```bash
# Generate from scratch
yamlgraph graph run examples/storyboard/animated-character-graph.yaml \
  --var concept="A detective solving a mystery" \
  --var model="hidream"

# With pre-existing character image (better consistency)
yamlgraph graph run examples/storyboard/animated-character-graph.yaml \
  --var concept="A detective solving a mystery" \
  --var model="hidream" \
  --var reference_image="path/to/character.png"
```

### How It Works

```
concept ──► expand_story ──► animate_panels (map) ──► generate_images
                │                    │                      │
                ▼                    ▼                      ▼
         character_prompt    3 panels × 3 prompts    9 images total
```

For each panel:
1. **Original** - Generated via:
   - `edit_image(reference_image, prompt)` if reference provided
   - `generate_image(character_prompt + panel.original)` otherwise
2. **First frame** - Generated via `edit_image(original, first_frame)` (img2img)
3. **Last frame** - Generated via `edit_image(original, last_frame)` (img2img)

Using `reference_image` ensures consistent character appearance across all panels.

### Output

```
outputs/storyboard/{thread_id}/animated/
├── panel_1_original.png
├── panel_1_first_frame.png
├── panel_1_last_frame.png
├── panel_2_original.png
├── panel_2_first_frame.png
├── panel_2_last_frame.png
├── panel_3_original.png
├── panel_3_first_frame.png
├── panel_3_last_frame.png
└── animated_character_story.json
```

### Files

| File | Purpose |
|------|---------|
| `animated-character-graph.yaml` | Animated graph with map node |
| `prompts/expand_character_story.yaml` | Story + character prompt |
| `prompts/animate_character_panel.yaml` | Panel → 3 frame prompts |
| `nodes/animated_character_node.py` | Image generation with img2img |

---

## Video Generation

After generating animated storyboard images, create video clips that interpolate between consecutive frames using the Wan 2.2 I2V model on Replicate.

### Usage

```bash
# Generate videos from animated storyboard images
python examples/storyboard/generate_videos.py outputs/storyboard/20260117_112419/animated

# Dry run - see what would be generated
python examples/storyboard/generate_videos.py outputs/storyboard/20260117_112419/animated --dry-run

# Custom options
python examples/storyboard/generate_videos.py outputs/storyboard/20260117_112419/animated \
  --fps 24 \
  --frames 81 \
  --resolution 720p \
  --prompt "Smooth cinematic motion"
```

### How It Works

```
panel_1_first_frame.png ──► clip_01.mp4 ──┐
panel_1_original.png    ──► clip_02.mp4 ──┤
panel_1_last_frame.png  ──► clip_03.mp4 ──┼──► final_combined.mp4
panel_2_first_frame.png ──► clip_04.mp4 ──┤
...                                       ┘
```

1. **Find images** - Sorts all PNGs alphabetically in the folder
2. **Generate clips** - Creates video for each consecutive pair using Replicate's `wan-video/wan-2.2-i2v-fast`
3. **Parallel processing** - Up to 4 clips generated simultaneously
4. **Concatenate** - Combines all clips into `final_combined.mp4` using ffmpeg

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--pattern` | `*.png` | Glob pattern for images |
| `--prompt` | auto | Motion prompt (extracted from metadata if available) |
| `--fps` | 16 | Frames per second |
| `--frames` | 81 | Number of frames per clip |
| `--resolution` | 480p | Output resolution (480p, 720p) |
| `--dry-run` | - | Preview without generating |

### Output

```
outputs/storyboard/{timestamp}/animated/videos/
├── clip_01_panel_1_first_frame_to_panel_1_original.mp4
├── clip_02_panel_1_original_to_panel_1_last_frame.mp4
├── clip_03_panel_1_last_frame_to_panel_2_first_frame.mp4
├── ...
└── final_combined.mp4   # All clips concatenated
```

### Requirements

- `REPLICATE_API_TOKEN` in `.env`
- `ffmpeg` installed for video concatenation (`brew install ffmpeg`)
