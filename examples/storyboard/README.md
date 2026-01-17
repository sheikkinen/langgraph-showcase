# Storyboard Generator

Generates a visual story with 3-5 panels from a concept using LLM + Replicate image generation.

## Usage

```bash
# Default (z-image model - photorealistic)
showcase graph run examples/storyboard/graph.yaml \
  --var concept="A wizard's apprentice discovers a hidden library"

# HiDream model (cartoon/illustration style)
showcase graph run examples/storyboard/graph.yaml \
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
