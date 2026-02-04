# Streaming Demo

Token-by-token LLM output streaming.

## Usage

```bash
python examples/demos/streaming/demo_streaming.py
```

## What It Does

Demonstrates real-time token streaming from LLM responses, useful for:
- Chat interfaces showing typing
- Long-running generations with progress
- Web UIs with SSE (Server-Sent Events)

## Key Concepts

- **`stream: true`** - Enable streaming on node
- **Async iteration** - Process tokens as they arrive
- **Callbacks** - Custom handlers for each token

## Code Pattern

```python
from yamlgraph.node_factory import create_streaming_node

# In graph config
nodes:
  generate:
    type: llm
    stream: true
    prompt: generate
```

## Use Cases

| Scenario | Benefit |
|----------|---------|
| Chat UI | Show typing indicator |
| Long generation | Progress feedback |
| SSE endpoint | Real-time updates |

## Related

- [reference/streaming.md](../../../reference/streaming.md)
- [fastapi_interview.py](../../fastapi_interview.py) - Streaming in FastAPI
