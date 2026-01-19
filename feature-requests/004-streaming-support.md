# Feature Request: Streaming Response Support

**ID:** 004  
**Priority:** P3 - Medium  
**Status:** ✅ Implemented  
**Effort:** 1 week  
**Requested:** 2026-01-19  
**Implemented:** 2026-01-19  
**Commit:** `93ea03c`  
**Docs:** [reference/streaming.md](../reference/streaming.md)

## Summary

Add streaming support for LLM responses, enabling token-by-token output for better user experience with long-form responses.

## Motivation

Current YamlGraph waits for complete LLM response before returning. For long responses (>500 tokens), this creates:
- Perceived latency (user waits 5-10 seconds with no feedback)
- Poor UX for conversational applications
- Timeout issues for very long responses

**Use case:** questionnaire-api recap summaries can be 200+ words. Streaming shows text as it generates.

## Proposed Solution

### YAML Configuration

```yaml
nodes:
  generate_summary:
    type: llm
    prompt: recap/generate_summary
    state_key: summary
    stream: true                    # Enable streaming
    stream_key: summary_stream      # Optional: where to emit chunks
```

### API

```python
from yamlgraph.executor_async import stream_node_output

# Stream a specific node's output
async for chunk in stream_node_output(
    graph="graphs/interview.yaml",
    node="generate_summary",
    state={"extracted_data": {...}},
):
    print(chunk, end="", flush=True)
```

### FastAPI SSE Integration

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from yamlgraph.executor_async import stream_node_output

@app.get("/stream/{session_id}")
async def stream_response(session_id: str):
    async def generate():
        async for chunk in stream_node_output(
            graph="graphs/interview.yaml",
            node="generate_response",
            config={"thread_id": session_id},
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
```

### HTMX Integration

```html
<!-- Frontend receives streaming updates -->
<div hx-ext="sse" sse-connect="/stream/session123">
    <div sse-swap="message" hx-swap="beforeend"></div>
</div>
```

### Implementation

```python
# yamlgraph/executor.py
from typing import AsyncIterator

async def execute_prompt_streaming(
    prompt_name: str,
    variables: dict,
    state: dict | None = None,
    **kwargs,
) -> AsyncIterator[str]:
    """Execute prompt with streaming output."""
    prompt_data = load_prompt(prompt_name)
    llm = create_llm(**kwargs)
    
    messages = build_messages(prompt_data, variables, state)
    
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield chunk.content


# yamlgraph/node_factory.py
def create_streaming_llm_node(node_name: str, node_config: dict):
    """Create LLM node with streaming support."""
    
    async def streaming_node(state: dict) -> AsyncIterator[dict]:
        prompt_name = node_config["prompt"]
        state_key = node_config.get("state_key", node_name)
        stream_key = node_config.get("stream_key", f"{state_key}_stream")
        
        full_response = ""
        
        async for chunk in execute_prompt_streaming(prompt_name, state):
            full_response += chunk
            yield {stream_key: chunk}  # Emit chunk
        
        # Final state update with complete response
        yield {state_key: full_response}
    
    return streaming_node
```

### Graph-Level Streaming

```python
# yamlgraph/executor_async.py
async def stream_graph_with_tokens(
    graph,
    initial_state: dict,
    config: dict,
) -> AsyncIterator[dict]:
    """Stream graph events including token-level LLM output."""
    app = graph.compile(checkpointer=config.get("checkpointer"))
    
    async for event in app.astream_events(initial_state, config, version="v2"):
        if event["event"] == "on_chat_model_stream":
            # Token from LLM
            yield {
                "type": "token",
                "node": event["metadata"].get("langgraph_node"),
                "content": event["data"]["chunk"].content,
            }
        elif event["event"] == "on_chain_end":
            # Node completed
            yield {
                "type": "node_complete",
                "node": event["metadata"].get("langgraph_node"),
                "output": event["data"]["output"],
            }
```

## Configuration Options

```yaml
nodes:
  response:
    type: llm
    prompt: dialogue/respond
    stream: true
    
    # Streaming options
    stream_options:
      buffer_size: 10          # Chars to buffer before emitting
      emit_interval: 100       # Minimum ms between emissions
      include_metadata: false  # Include token metadata
```

## Acceptance Criteria

- [ ] `stream: true` option in YAML
- [ ] `execute_prompt_streaming()` yields tokens
- [ ] `stream_graph_with_tokens()` for full graph streaming
- [ ] SSE-compatible output format
- [ ] Buffer/debounce options
- [ ] Works with structured output (stream text, validate at end)
- [ ] FastAPI SSE example
- [ ] HTMX example in docs

## Related

- Feature #003: Async Executor (required)
- LangGraph streaming: https://langchain-ai.github.io/langgraph/how-tos/stream-values/
