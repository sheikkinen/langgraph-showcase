# Shared Utilities

Reusable tools for YAMLGraph examples.

## Available Tools

### `websearch.py` - Web Search

DuckDuckGo-based web search. No API key required.

```yaml
# In agent node
tools:
  search_web:
    type: python
    module: examples.shared.websearch
    function: search_web
    description: "Search the web for information"
```

**Requirements:** `pip install ddgs`

### `replicate_tool.py` - Image Generation

Replicate API for image generation with multiple model presets.

| Model | Best For | Speed |
|-------|----------|-------|
| `z-image` | Realistic/photographic (default) | Fast |
| `hidream` | Cartoons, illustrations, stylized | Fast |

```python
from examples.shared.replicate_tool import generate_image, ImageResult

result: ImageResult = generate_image(
    prompt="A mystical forest at dawn",
    output_dir="outputs/images",
    model="z-image"  # or "hidream"
)
```

**Requirements:** `pip install replicate` + `REPLICATE_API_TOKEN` env var

## Scripts

### `scripts/set_fly_secrets.sh`

Helper for setting Fly.io secrets (used by `daily_digest/`).
