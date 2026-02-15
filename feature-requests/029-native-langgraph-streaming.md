# Feature Request: Native LangGraph Token Streaming

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Implemented
**Effort:** 2 days (reduced from 3 — no node changes needed)
**Requested:** 2026-02-12
**Research Completed:** 2026-02-12
**Implemented:** 2026-02-12

## Summary

Native `astream(stream_mode="messages")` streaming via `run_graph_streaming_native()` enables token-by-token streaming from ALL LLM nodes in a graph, including mid-loop nodes.

## How to Use

### Basic Streaming

```python
from yamlgraph.executor_async import run_graph_streaming_native

async for token in run_graph_streaming_native(
    "graph.yaml",
    {"input": "hello"},
):
    print(token, end="", flush=True)
```

### With Checkpointer (Multi-Turn)

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "session-123"}}

# Turn 1
async for token in run_graph_streaming_native(
    "graph.yaml", {"input": "hi"}, config
):
    print(token, end="")

# Turn 2 (resume)
async for token in run_graph_streaming_native(
    "graph.yaml", Command(resume="continue"), config
):
    print(token, end="")
```

### Filter to Specific Node

```python
# Only stream from 'respond' node (useful in multi-LLM graphs)
async for token in run_graph_streaming_native(
    "multi_llm.yaml",
    {"input": "hi"},
    node_filter="respond",
):
    print(token, end="")
```

### SSE Integration

See `examples/openai_proxy/` for OpenAI-compatible SSE format.

### Related Documentation

- [reference/streaming.md](../reference/streaming.md) — Full API reference
- [reference/checkpointers.md](../reference/checkpointers.md) — Checkpoint configuration
- [examples/openai_proxy/](../examples/openai_proxy/) — SSE proxy example
- [examples/demos/multi-turn/](../examples/demos/multi-turn/) — Multi-turn example

---

## Original Problem Statement

### Current Architecture Limitation

The legacy `run_graph_streaming()` (FR-023, FR-028) used a workaround strategy:

```python
# Current approach (executor_async.py:356-395)
# 1. Deep-copy graph config with LLM node set to passthrough
config_pre.nodes[llm_node_name]["type"] = "passthrough"

# 2. Run entire graph to build state (no streaming)
pre_state = await compiled.ainvoke(initial_state, config)

# 3. Manually stream only the first LLM node found
async for token in execute_prompt_streaming(...):
    yield token
```

**Limitations:**
- Only streams the **first** LLM node found in node iteration order
- Cannot stream LLM nodes in the middle of a loop (e.g., `respond → wait_for_user → respond`)
- If interrupt occurs before LLM node, no tokens are streamed
- Graphs with multiple LLM nodes only stream the first one
- State from LLM response is computed after streaming, not during

### Violated Objective

FR-028 (Multi-Turn Streaming) documented this gap:

> "Token-by-token streaming of mid-loop LLM nodes requires LangGraph's native `astream(stream_mode="messages")` integration, planned for future enhancement."

Multi-turn conversation graphs typically have LLM nodes in loops where the workaround doesn't work.

### LangGraph Native Capability

LangGraph provides `astream(stream_mode="messages")` which:
- Streams `(AIMessageChunk, metadata)` tuples as tokens arrive
- Works with **any** ChatModel node in the graph
- Compatible with checkpointers and interrupts
- Streams from all LLM nodes, not just the first one
- Maintains proper state updates during streaming

---

## Proposed Solution

### Phase 1: Research & Design (0.5 days)

1. Create test graph with multiple LLM nodes and interrupt
2. Verify `stream_mode="messages"` behavior with yamlgraph-compiled graphs
3. Document event format: `(AIMessageChunk, metadata)` tuple structure
4. Identify node name in metadata for filtering

### Phase 2: Core Implementation (1.5 days)

New function using native LangGraph streaming:

```python
# yamlgraph/executor_async.py

async def run_graph_streaming_native(
    graph_path: str,
    initial_state: dict | Command,
    config: dict | None = None,
    node_filter: str | None = None,  # Optional: only stream from specific node
) -> AsyncIterator[str | Interrupt]:
    """Execute graph with native LangGraph token streaming.

    Uses LangGraph's astream(stream_mode="messages") for true token-by-token
    streaming from any LLM node in the graph.

    Args:
        graph_path: Path to graph YAML file
        initial_state: Initial state or Command(resume=...)
        config: LangGraph config with thread_id
        node_filter: If set, only yield tokens from this node name

    Yields:
        - str: Token strings from LLM nodes
        - Interrupt: When graph hits interrupt

    Example:
        >>> async for chunk in run_graph_streaming_native(
        ...     "graph.yaml",
        ...     {"input": "hello"},
        ...     {"configurable": {"thread_id": "t1"}},
        ... ):
        ...     if isinstance(chunk, Interrupt):
        ...         break
        ...     print(chunk, end="", flush=True)
    """
    from langgraph.types import Interrupt

    app = await load_and_compile_async(graph_path)
    config = config or {}

    async for event in app.astream(
        initial_state,
        config,
        stream_mode="messages",
    ):
        # event is (AIMessageChunk, metadata) tuple
        chunk, metadata = event

        # Handle interrupt events
        if isinstance(chunk, Interrupt):
            yield chunk
            return

        # Extract node name from metadata for filtering
        node_name = metadata.get("langgraph_node")
        if node_filter and node_name != node_filter:
            continue

        # Yield token content
        if hasattr(chunk, "content") and chunk.content:
            yield chunk.content
```

### Phase 3: Migration & Deprecation (0.5 days)

1. Keep `run_graph_streaming()` for backward compatibility
2. Add deprecation warning pointing to `run_graph_streaming_native()`
3. Document migration path in README

### Phase 4: Integration Tests (0.5 days)

```python
@pytest.mark.req("REQ-YG-065")
async def test_native_streaming_multi_llm_graph():
    """Stream tokens from a graph with multiple LLM nodes."""
    tokens = []
    async for token in run_graph_streaming_native(
        "examples/demos/multi-llm/graph.yaml",
        {"input": "hello"},
    ):
        tokens.append(token)
    assert len(tokens) > 0

@pytest.mark.req("REQ-YG-065")
async def test_native_streaming_mid_loop_node():
    """Stream tokens from LLM node in the middle of a loop."""
    # respond → wait_for_user → respond pattern
    ...

@pytest.mark.req("REQ-YG-065")
async def test_native_streaming_with_node_filter():
    """Only stream from specific node when multiple LLMs exist."""
    ...
```

---

## Acceptance Criteria

- [x] New `run_graph_streaming_native()` using `astream(stream_mode="messages")`
- [x] Streams tokens from any LLM node, not just first found
- [x] Works with mid-loop LLM nodes (respond → wait → respond pattern)
- [x] Supports checkpointer — accepts `config` with thread_id
- [x] Optional `node_filter` to select specific LLM node
- [x] No node implementation changes required (validated by research)
- [x] Legacy `run_graph_streaming()` removed (was deprecated)
- [x] Unit tests for streaming behavior (7 tests)
- [x] Integration tests (5 tests)
- [x] README documentation updated
- [x] REQ-YG-065 defined in ARCHITECTURE.md

---

## Alternatives Considered

### 1. Keep Current Approach

**Rejected.** The passthrough hack only works for linear graphs ending with a single LLM node. Multi-turn and complex graphs are increasingly common.

### 2. stream_mode="updates" with Custom Events

Could use `stream_mode="updates"` and inject custom streaming events in node implementations.

**Rejected.** Would require changing every LLM node implementation. Native `messages` mode handles this automatically.

### 3. Hybrid: Native for Multi-LLM, Legacy for Simple

Keep both implementations, auto-detect which to use based on graph structure.

**Considered.** May add complexity. Prefer single native approach with deprecation path.

---

## Technical Notes

### LangGraph stream_mode Options

From LangGraph source (`langgraph.types.StreamMode`):
- `'values'` — Full state after each node
- `'updates'` — Incremental state updates
- `'checkpoints'` — Checkpoint data
- `'tasks'` — Task execution info
- `'debug'` — Debug info
- **`'messages'`** — AIMessage tokens from LLMs ✓
- `'custom'` — Custom events

### Event Structure for messages Mode

```python
async for event in graph.astream(input, config, stream_mode="messages"):
    chunk, metadata = event
    # chunk: AIMessageChunk with .content attribute
    # metadata: dict with 'langgraph_node', 'langgraph_step', etc.
    token = chunk.content  # The actual token string
    node = metadata.get("langgraph_node")  # Which node emitted this
```

### Compatibility Requirements

- Requires LangGraph >= 0.2.0 (messages stream mode)
- Works with any langchain ChatModel (Anthropic, OpenAI, etc.)
- Compatible with MemorySaver, SqliteSaver, RedisSaver checkpointers

---

## Research Findings (2026-02-12)

Spike script: `scripts/spike_fr029_streaming.py`

### Q1: Does `stream_mode="messages"` require nodes to use `astream` internally?

**NO.** LangGraph uses a callback handler (`StreamMessagesHandler` in `langgraph/pregel/_messages.py`) that intercepts LLM tokens at the callback level. Nodes using `llm.ainvoke()` still stream tokens — **no node implementation changes required.**

Test result:
```
TEST 1: stream_mode='messages' with ainvoke node
  Token 1: AIMessageChunk from 'llm': 'Hello'
  Token 2: AIMessageChunk from 'llm': ' there'
  Token 3: AIMessageChunk from 'llm': ' frien'
  Token 4: AIMessageChunk from 'llm': 'd!'
Result: Received 4 tokens from ainvoke node
```

### Q2: What is the exact event structure?

**Confirmed:** `(AIMessageChunk, dict)` tuple.

```python
# Event structure from TEST 2:
Event type: <class 'tuple'>
  [0] AIMessageChunk
      .content = ''  # or token text
      .id = 'lc_run--...'
  [1] dict
      ['langgraph_step'] = 1
      ['langgraph_node'] = 'llm'  # ✓ node identification
      ['langgraph_triggers'] = ('branch:to:llm',)
      ['ls_provider'] = 'anthropic'
      ['ls_model_name'] = 'claude-sonnet-4-20250514'
```

### Q3: How are interrupts surfaced in messages mode?

**Interrupts do NOT appear in the stream.** After streaming completes, check `final_state.next`:

```python
# From TEST 3:
Final state has __interrupt__: False
Next nodes: ('wait',)  # ← interrupt pending at 'wait' node
```

Update proposed API: instead of yielding `Interrupt`, check state after iteration.

### Q4: Do multiple LLM nodes all stream?

**YES.** Both nodes stream tokens, distinguished by `metadata['langgraph_node']`:

```
TEST 4: Multiple LLM nodes
  llm_1: '1'
  llm_1: '\n2\n3'
  llm_2: 'A'
  llm_2: ','
  llm_2: ' B, C'
Tokens by node: {'llm_1': 2, 'llm_2': 3}
```

### Q5: Does it work with yamlgraph-compiled graphs?

**YES.** Tested with `examples/demos/hello/graph.yaml`:

```
TEST 5: yamlgraph-compiled graph
  Token 1 from 'greet': 'Hey'
  Token 2 from 'greet': ' World'
  Token 3 from 'greet': '!'
Result: Received 5 tokens from yamlgraph-compiled graph
```

### Updated Implementation Plan

Based on findings, revise Phase 2 implementation:

```python
async def run_graph_streaming_native(
    graph_path: str,
    initial_state: dict | Command,
    config: dict | None = None,
    node_filter: str | None = None,
) -> AsyncIterator[str]:
    """Native LangGraph token streaming.

    Yields:
        str: Token strings from all LLM nodes (or filtered node)

    Note:
        Does not yield Interrupt. After iteration, check graph state
        for pending interrupts via `app.aget_state(config).next`.
    """
    app = await load_and_compile_async(graph_path)
    config = config or {}

    async for event in app.astream(initial_state, config, stream_mode="messages"):
        chunk, metadata = event
        node_name = metadata.get('langgraph_node')
        if node_filter and node_name != node_filter:
            continue
        if hasattr(chunk, 'content') and chunk.content:
            yield chunk.content
```

**Key change:** Remove `| Interrupt` from return type — interrupts are state, not stream events.

---

## Related

- [FR-023](023-graph-level-streaming.md) — Original graph streaming implementation
- [FR-028](028-multi-turn-streaming.md) — Multi-turn streaming (documented this limitation)
- [examples/demos/multi-turn/](../examples/demos/multi-turn/) — Multi-turn example using run_graph_async
- [executor_async.py](../yamlgraph/executor_async.py) — Current streaming implementation
- [scripts/spike_fr029_streaming.py](../scripts/spike_fr029_streaming.py) — Research spike
- LangGraph docs: [Streaming](https://langchain-ai.github.io/langgraph/how-tos/streaming/)
