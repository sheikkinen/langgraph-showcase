# Feature Request: Multi-Turn Streaming with Guard Classification

**Priority:** HIGH
**Type:** Feature
**Status:** Proposed
**Effort:** 2-3 days
**Requested:** 2026-02-12

## Summary

Extend `openai_proxy` example to demonstrate multi-turn streaming with session resume and pre-stream guard classification. Currently `openai_proxy` handles single-shot requests (one graph invocation, no state between requests). Consumers need multi-turn conversations with state persistence and conditional routing.

## Problem

### Violated Objective

The `openai_proxy` example demonstrates single-shot streaming via `run_graph_streaming()` (FR-023). Voice AI integrations (OpenAI-compatible Custom LLM endpoints) require multi-turn conversations where each HTTP request resumes a graph from its last interrupt.

### Architectural Gap

```
Current (single-shot):
  POST /v1/chat/completions → run_graph_streaming() → SSE → [DONE]
  (no state between requests, no resume)

Desired (multi-turn):
  POST turn 1 → run_graph_streaming(initial_state, config) → SSE → interrupt
  POST turn 2 → run_graph_streaming(Command(resume=msg), config) → SSE → interrupt
  ...
  POST turn N → run_graph_streaming(Command(resume=msg), config) → SSE → [DONE]
```

Additionally, before streaming the main graph, a fast guard classification should decide whether to proceed or redirect (e.g., user says "stop" or "help" mid-conversation).

### Why This Matters

This is the most common LLM application pattern: multi-turn conversations with intent routing. Without a reference example, consumers must build custom streaming + state management on top of yamlgraph, bypassing the framework — which undermines its value.

## Proposed Solution

### Pattern: Guard + Content Streaming

```
POST /v1/chat/completions {messages: [...]}
    │
    ├─ 1. Extract latest user message
    │
    ├─ 2. Guard / pre-execution classification (fast model, ~200ms)
    │       │
    │       ├─ redirect → Stream short response, don't run main graph
    │       └─ continue → Proceed to step 3
    │
    └─ 3. Main graph streaming
            │
            ├─ Resume from checkpointer (thread_id from session)
            ├─ Command(resume=user_message)
            └─ Stream tokens via SSE
```

The guard could be implemented as a separate graph, a pre-hook, a first node — whatever fits yamlgraph's architecture best. The key requirement: classify before streaming, conditionally skip main graph.

### Multi-Turn with Checkpointer

```python
# Pseudo-code for the pattern needed
config = {"configurable": {"thread_id": session_id}}

# First turn: invoke with initial state
result = await run_graph_streaming(graph_path, initial_state, config)

# Subsequent turns: resume from checkpoint
result = await run_graph_streaming(graph_path, Command(resume=message), config)
```

**Key question:** Does `run_graph_streaming()` support `Command(resume=...)` input? Current signature takes `initial_state: dict`. Resume requires `Command` object.

### Concrete Example Scenario

Suggested: extend `examples/questionnaire/` to streaming.

- Graph collects 3 answers via interrupts (multi-turn)
- Guard: if user says "stop" or "help", redirect instead of continuing
- Each turn streams the next question token-by-token
- Session resumes on each POST via `thread_id`
- Uses `MemorySaver` checkpointer

### OpenAI-Compatible SSE

All responses (guard redirect and content) use OpenAI streaming format:

```
data: {"choices": [{"delta": {"content": "token"}}]}
data: {"choices": [{"delta": {"content": "next"}}]}
data: [DONE]
```

## Acceptance Criteria

- [ ] Example starts new session on first request (no existing thread_id)
- [ ] Example resumes session on subsequent requests (existing thread_id)
- [ ] Guard classification runs before main graph (sequential)
- [ ] Main graph streams tokens via SSE
- [ ] Guard redirect returns streamed response (skips main graph)
- [ ] State persists between requests via checkpointer
- [ ] Works with `MemorySaver`
- [ ] Tests cover: new session, resume, guard redirect, multi-turn completion
- [ ] Tests added
- [ ] Documentation updated

## Alternatives Considered

1. **Consumer builds custom streaming** — defeats framework purpose; every consumer reimplements the same pattern.
2. **Guard as graph node** — possible but requires yamlgraph to support conditional early-exit from graph mid-execution. May be the best solution; requesting team guidance.
3. **No guard, just multi-turn** — simpler scope but misses the routing requirement that most voice AI integrations need.

## Technical Questions

1. **`run_graph_streaming()` + resume:** Does it accept `Command(resume=...)` or only `dict` initial state?
2. **Checkpointer injection:** How to pass checkpointer to `run_graph_streaming()`? Current `openai_proxy` uses `load_and_compile()` which doesn't take checkpointer.
3. **Graph config propagation:** Can `thread_id` be passed through `run_graph_streaming()` config?
4. **Interrupt handling in streaming:** When graph hits an interrupt, does streaming yield the interrupt value and stop? Or does it need special handling?

## Related

- FR-023: Graph-Level Streaming (`023-graph-level-streaming.md`) — prerequisite, provides `run_graph_streaming()`
- `examples/openai_proxy/` — current single-shot streaming example
- `examples/questionnaire/` — existing multi-turn interrupt-based graph (candidate base)
- `yamlgraph/executor_async.py` — `run_graph_streaming()` implementation
- LangGraph `Command(resume=...)` — [LangGraph docs](https://langchain-ai.github.io/langgraph/)
