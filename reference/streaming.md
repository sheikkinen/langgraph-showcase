# Streaming

Stream LLM output token-by-token for real-time UX.

## Quick Start

```python
from yamlgraph.executor_async import execute_prompt_streaming

async for token in execute_prompt_streaming("greet", {"name": "World"}):
    print(token, end="", flush=True)
```

Output appears as it's generated:
```
H e l l o ,   W o r l d !
```

## execute_prompt_streaming

Async generator that yields tokens as they're produced.

```python
async def execute_prompt_streaming(
    prompt_name: str,
    variables: dict | None = None,
    temperature: float = 0.7,
    provider: str | None = None,
) -> AsyncIterator[str]:
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt_name` | str | required | Prompt file name (without .yaml) |
| `variables` | dict | `{}` | Template variables |
| `temperature` | float | `0.7` | LLM temperature |
| `provider` | str | from env/YAML | `"anthropic"`, `"google"`, `"mistral"`, `"openai"` |

### Example

```python
import asyncio
from yamlgraph.executor_async import execute_prompt_streaming

async def main():
    full_response = ""

    async for token in execute_prompt_streaming(
        "greet",
        variables={"name": "Alice", "style": "friendly"},
        provider="mistral",
    ):
        print(token, end="", flush=True)
        full_response += token

    print(f"\n\nTotal: {len(full_response)} chars")

asyncio.run(main())
```

## YAML Node Config

Enable streaming for graph nodes:

```yaml
nodes:
  generate:
    type: llm
    prompt: my-prompt
    stream: true  # Enable streaming
    state_key: response
```

### Streaming Node Factory

```python
from yamlgraph.node_factory import create_streaming_node

node_config = {
    "prompt": "greet",
    "state_key": "greeting",
    "on_token": lambda t: print(t, end=""),  # Optional callback
}

streaming_node = create_streaming_node("generate", node_config)

async for token in streaming_node(state):
    # Process each token
    pass
```

## Collecting Tokens

Collect all tokens into a string:

```python
response = "".join([
    token async for token in execute_prompt_streaming("greet", {"name": "World"})
])
```

Or with a list:

```python
tokens = []
async for token in execute_prompt_streaming("greet", {"name": "World"}):
    tokens.append(token)

response = "".join(tokens)
print(f"Received {len(tokens)} chunks")
```

## Server-Sent Events (SSE)

Stream to web clients with SSE:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from yamlgraph.executor_async import execute_prompt_streaming

app = FastAPI()

@app.get("/stream")
async def stream(prompt: str):
    async def generate():
        async for token in execute_prompt_streaming("chat", {"query": prompt}):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

Frontend:
```javascript
const eventSource = new EventSource('/stream?prompt=hello');
eventSource.onmessage = (e) => {
    if (e.data === '[DONE]') {
        eventSource.close();
    } else {
        document.getElementById('output').textContent += e.data;
    }
};
```

## Limitations

1. **No structured output**: Streaming bypasses Pydantic validation. Use `execute_prompt_async` with `output_model` for structured responses.

2. **Empty chunks skipped**: The streaming function automatically filters out empty chunks.

3. **Error handling**: Errors are propagated. Wrap in try/except:

```python
try:
    async for token in execute_prompt_streaming("greet", {}):
        print(token, end="")
except Exception as e:
    print(f"\nError: {e}")
```

## Demo

Run the streaming demo:

```bash
# Real LLM streaming
python scripts/demo_streaming.py

# Mock mode (no LLM)
python scripts/demo_streaming.py --verify
```

## Graph-Level Streaming (FR-023)

Stream an entire graph's LLM output token-by-token. Non-LLM nodes (python, tool)
run first, then the LLM node streams.

```python
from yamlgraph.executor_async import run_graph_streaming

async for token in run_graph_streaming(
    graph_path="examples/openai_proxy/graph.yaml",
    initial_state={"input": "Hello!"},
):
    print(token, end="", flush=True)
```

### How It Works

1. Loads the graph config and identifies the LLM node
2. Replaces the LLM node with a passthrough and runs pre-processing nodes
3. Streams the LLM node via `llm.astream()`, yielding tokens

### Signature

```python
async def run_graph_streaming(
    graph_path: str,
    initial_state: dict,
) -> AsyncIterator[str]:
```

### OpenAI-Compatible SSE Proxy

The `examples/openai_proxy/` uses `run_graph_streaming()` to serve real
token-by-token SSE streams via the OpenAI `/v1/chat/completions` API:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://yamlgraph-proxy.fly.dev/v1",
    api_key="your-web-api-key",
)

# Streaming
for chunk in client.chat.completions.create(
    model="gemini-2.5-flash",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True,
):
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

Demo script:

```bash
# Non-streaming
python examples/openai_proxy/demo.py

# Streaming
python examples/openai_proxy/demo.py --stream

# Verify mode (no server needed)
python examples/openai_proxy/demo.py --verify
```

## See Also

- [Async Usage](async-usage.md) - Full async API reference
- [Prompt YAML](prompt-yaml.md) - Prompt configuration
