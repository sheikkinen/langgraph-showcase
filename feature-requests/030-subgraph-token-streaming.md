# Feature Request: Subgraph Token Streaming

**Component:** yamlgraph  
**Version:** 0.4.36  
**LangGraph:** 1.0.6  
**Date:** 2026-02-13  
**Priority:** High  
**Status:** Phase 1 Complete (0.4.37)

## Implementation Status

| Phase | Status | Version |
|-------|--------|---------|
| Bug Fix (dict token guard) | ✅ Complete | 0.4.37 |
| Phase 1 (subgraphs param) | ✅ Complete | 0.4.37 |
| Phase 2 (async mode=invoke) | 🔬 Research Complete | TBD |
| Phase 3 (namespace node_filter) | ⏸️ Deferred | TBD |

### How to Use (0.4.37+)

```python
# Stream from mode=direct subgraphs
async for token in run_graph_streaming_native(
    "parent.yaml",
    {"input": "hello"},
    subgraphs=True,  # Enable subgraph streaming
):
    print(token, end="")

# Router graphs now work (dict content auto-filtered)
async for token in run_graph_streaming_native(
    "router.yaml",
    {"message": "I love this!"},
):
    print(token, end="")  # Only string tokens, no crash
```

## Phase 2 Research Findings (2026-02-13)

**Spike:** `scripts/spike_subgraph_streaming.py`

### Validated Root Cause

1. **Callbacks DO propagate** — all LLM nodes (parent and child) receive `on_chat_model_start`
2. **Namespace filtering blocks tokens** — child's namespace is nested (e.g., `summarize:...|summarize:...`)
3. **Direct `astream()` WORKS** — calling child's `astream(stream_mode="messages")` yields tokens
4. **Sync `invoke()` blocks streaming** — opaque boundary prevents token forwarding

### Confirmed Approach

Convert `mode=invoke` wrapper from sync `def` to `async def`:
- Replace `compiled.invoke()` with `compiled.astream(stream_mode="messages")`
- Collect tokens and forward to parent stream via callback or runtime.stream_writer
- Preserve `interrupt_output_mapping` and `GraphInterrupt` handling

### Implementation Plan

```python
async def subgraph_node_async(state: dict, config: RunnableConfig | None = None):
    \"\"\"Async subgraph node with streaming support.\"\"\"
    # 1. Map input state
    child_input = _map_input_state(state, input_mapping)
    
    # 2. Get parent's stream_writer from runtime
    runtime = config.get("configurable", {}).get(CONFIG_KEY_RUNTIME)
    
    # 3. Stream from child, forwarding tokens
    async for event in compiled.astream(child_input, child_config, stream_mode="messages"):
        chunk, meta = event
        if runtime and hasattr(runtime, "stream_writer"):
            runtime.stream_writer(chunk)  # Forward to parent
    
    # 4. Get final state and map output
    child_state = compiled.get_state(child_config)
    return _map_output_state(child_state.values, output_mapping)
```

## Summary

`run_graph_streaming_native` does not emit LLM tokens from subgraph nodes. When a parent graph routes to a subgraph containing LLM nodes, the subgraph executes correctly but zero streaming tokens reach the caller. This makes voice/SSE use cases impossible for graphs that use subgraph composition.

## Reproduction

```yaml
# parent/graph.yaml — router + subgraph with different state schemas
state:
  user_message: str
  response: str
  result: dict
  original_intent: str

nodes:
  classify:
    type: router
    prompt: classify
    routes:
      alcohol: run_audit
    default_route: run_audit

  run_audit:
    type: subgraph
    graph: ../audit/graph.yaml       # Has its own state: extracted, gaps, schema, etc.
    input_mapping:
      user_message: user_message
    output_mapping:
      result: result
      response: response

edges:
  - from: START
    to: classify
  - from: classify
    to: [run_audit]
    type: conditional
  - from: run_audit
    to: END
```

```python
# caller
async for token in run_graph_streaming_native(
    graph_path="parent/graph.yaml",
    initial_state={"user_message": "hello"},
    config={"configurable": {"thread_id": "test-1"}},
):
    print(token)  # Never prints — 0 tokens from subgraph LLM nodes
```

The subgraph's LLM nodes (e.g. `generate_opening`, `generate_recap`) execute and produce correct state, but their streaming tokens are invisible to the parent's `astream()` call.

## Root Cause Analysis

### Issue 1: `subgraphs=False` (default)

`run_graph_streaming_native` calls `astream()` without `subgraphs=True`:

```python
# executor_async.py:290 — current code
async for event in app.astream(initial_state, config, stream_mode="messages"):
    chunk, metadata = event
    # ...
    yield chunk.content
```

LangGraph's `astream()` accepts `subgraphs: bool = False`. When `True`, events from subgraph nodes are emitted as `(namespace, payload)` tuples (for single stream_mode), where `namespace` is a tuple like `("run_audit:<task_id>",)` and `payload` is the `(chunk, metadata)` pair.

Without `subgraphs=True`, `StreamMessagesHandler.on_chat_model_start` returns early for any event with a non-root namespace — subgraph token events are never enqueued into the parent's stream in the first place.

### Issue 2: `mode=invoke` uses synchronous `compiled.invoke()`

Even with `subgraphs=True`, `mode=invoke` subgraphs cannot stream because the subgraph is wrapped in a synchronous Python function (`def`, not `async def`):

```python
# node_factory/subgraph_nodes.py — mode=invoke
def subgraph_node(state: dict, config: RunnableConfig | None = None) -> dict:
    child_input = _map_input_state(state, input_mapping)
    child_output = compiled.invoke(child_input, child_config)  # Sync, blocking
    return _map_output_state(child_output, output_mapping)
```

LangGraph cannot see inside this opaque function call. The `compiled.invoke()` runs the entire child graph to completion, consuming all LLM tokens internally. The parent's `CONFIG_KEY_STREAM` does not propagate through the invoke wrapper, so child LLM events never reach the parent stream queue.

Only `mode=direct` subgraphs (which return the `CompiledStateGraph` directly) are visible to LangGraph's subgraph streaming, because LangGraph natively manages their execution lifecycle.

### Issue 3: `node_filter` is top-level only

```python
node_name = metadata.get("langgraph_node")
if node_filter and node_name != node_filter:
    continue
```

This matches exact top-level node names. With `subgraphs=True`, subgraph events include namespace prefixes (e.g. `"run_audit:<task_id>"`) and nested node names. The current filter cannot match subgraph-internal nodes.

## Proposed Solution

### Phase 1: Enable `subgraphs=True` passthrough + type guard

Add a `subgraphs` parameter to `run_graph_streaming_native` and fix event unpacking:

```python
async def run_graph_streaming_native(
    graph_path: str,
    initial_state: dict | Command,
    config: dict | None = None,
    node_filter: str | None = None,
    subgraphs: bool = False,          # NEW
) -> AsyncIterator[str]:
    app = await load_and_compile_async(graph_path)
    config = config or {}

    async for event in app.astream(
        initial_state, config,
        stream_mode="messages",
        subgraphs=subgraphs,          # Pass through
    ):
        # Single stream_mode + subgraphs=True yields (namespace, payload)
        # Single stream_mode + subgraphs=False yields payload directly
        # where payload = (BaseMessage, metadata_dict)
        if subgraphs:
            _namespace, payload = event
            chunk, metadata = payload
        else:
            chunk, metadata = event

        node_name = metadata.get("langgraph_node")
        if node_filter and node_name != node_filter:
            continue
        if hasattr(chunk, "content") and chunk.content and isinstance(chunk.content, str):
            yield chunk.content
```

**Scope:** This enables streaming from `mode=direct` subgraphs only. No breaking changes to existing callers (default `subgraphs=False` preserves current behavior).

**Limitation:** `mode=direct` requires parent and child graphs to share a compatible state schema. It does not support `input_mapping` / `output_mapping` (these are silently ignored, not validated). For graphs where parent and child have different state fields (the common case), `mode=direct` is not a drop-in replacement — Phase 2 is needed.

### Phase 2: Async streaming for `mode=invoke` (primary need)

This is the critical phase for real-world use cases where parent and child graphs have different state schemas (e.g. navigator has `original_intent`, `priority_response` while audit has `extracted`, `gaps`, `schema_path`). `mode=invoke` exists precisely to bridge these schema differences via `input_mapping` / `output_mapping`.

To enable streaming from `mode=invoke` subgraphs:

1. Convert the wrapper to `async def subgraph_node`
2. Replace `compiled.invoke()` with `compiled.astream()` or propagate `CONFIG_KEY_STREAM` to enable parent stream forwarding
3. Preserve `input_mapping` / `output_mapping` application
4. Preserve `interrupt_output_mapping` and `GraphInterrupt` handling
5. Collect final state from the async stream for output mapping

One approach: propagate the parent's `CONFIG_KEY_STREAM` into the child config so that LLM token callbacks from the child graph write directly into the parent's stream queue. This avoids rewriting the invoke wrapper into a full `astream` consumer.

Alternative: use LangGraph's callback mechanism to forward `on_llm_new_token` events from the child graph to the parent stream.

### Phase 3: Namespace-aware `node_filter`

Extend `node_filter` to support patterns for subgraph nodes:

```python
# Simple: match any node with this name at any depth
node_filter="generate_opening"

# Namespaced: match specific subgraph path
node_filter="run_audit:generate_opening"

# Glob: match all LLM nodes in a subgraph
node_filter="run_audit:*"
```

## Impact

Without subgraph streaming, any graph that uses composition (parent → subgraph routing) cannot provide real-time token output. This affects:

- **Voice integrations** (ElevenLabs, Twilio) that require token-by-token SSE streaming for low-latency speech synthesis
- **Chat UIs** that show progressive text generation
- **Any SSE/WebSocket endpoint** backed by a composed graph

The workaround today is to call the leaf graph directly (e.g. `model=audit` instead of `model=navigator`), bypassing the parent router entirely. This defeats the purpose of graph composition.

## Separate Bug: Non-string Token from Router Nodes

_This is a distinct issue affecting all graphs with router nodes, not specific to subgraphs. Filed here for visibility; should be tracked separately._

Router nodes (`type: router`) emit dict tokens (their classification result) through the `astream(stream_mode="messages")` pipeline. The `chunk.content` for these is a `dict`, not a `str`. Callers that iterate tokens and assume string content will crash with `TypeError: can only concatenate str (not "dict") to str`.

```python
# Current code yields chunk.content which may be dict
yield chunk.content  # TypeError if chunk.content is dict
```

Fix: add a type guard in `run_graph_streaming_native`:

```python
if hasattr(chunk, "content") and chunk.content and isinstance(chunk.content, str):
    yield chunk.content
```

This guard is already included in the Phase 1 proposal above.

## References

- LangGraph `astream()` subgraphs parameter: `langgraph/pregel/main.py:2681`
- LangGraph `_output()` yield logic: `langgraph/pregel/main.py:3252`
- LangGraph `StreamMessagesHandler.on_chat_model_start`: `langgraph/pregel/_messages.py:131` (namespace filtering)
- LangGraph `StreamChunk` type: `langgraph/pregel/protocol.py:148` — `tuple[tuple[str, ...], str, Any]`
- yamlgraph subgraph factory: `yamlgraph/node_factory/subgraph_nodes.py`
- yamlgraph streaming: `yamlgraph/executor_async.py:290`
- LangGraph docs: [How to stream from subgraphs](https://langchain-ai.github.io/langgraph/how-tos/streaming-subgraphs/)

### LangGraph `astream()` Event Shapes

| `stream_mode` | `subgraphs` | Yielded shape |
|---|---|---|
| `"messages"` (str) | `False` | `(BaseMessage, metadata_dict)` |
| `"messages"` (str) | `True` | `(namespace_tuple, (BaseMessage, metadata_dict))` |
| `["messages"]` (list) | `False` | `("messages", (BaseMessage, metadata_dict))` |
| `["messages"]` (list) | `True` | `(namespace_tuple, "messages", (BaseMessage, metadata_dict))` |

Where `namespace_tuple` = `tuple[str, ...]`, e.g. `()` for root, `("run_audit:<task_id>",)` for child.
