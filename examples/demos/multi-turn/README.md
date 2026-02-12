# Multi-Turn Streaming Demo (FR-028)

Demonstrates multi-turn conversations with interrupt/resume and guard classification.

## Features

1. **Multi-Turn with Checkpointer** — State persists across HTTP requests via MemorySaver
2. **Interrupt/Resume** — Graph pauses at interrupt, resumes with Command
3. **Guard Classification** — Separate fast call to classify intent before main flow

## Graph Flow

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │  wait   │  ← interrupt (get user input)
                    └────┬────┘
                         │ (resume)
                    ┌────▼────┐
                    │ respond │  ← LLM generates response
                    └────┬────┘
                         │
                         └───► wait (loop)
```

**Turn flow:**
- Turn 1: START → wait_for_user (interrupt immediately)
- Turn 2: resume → respond (LLM) → wait_for_user (interrupt)
- Turn 3+: resume → respond → wait_for_user (loop)

## Usage

### Multi-Turn with Checkpointer

```python
from langgraph.types import Command
from yamlgraph.executor_async import load_and_compile_async, run_graph_async

app = await load_and_compile_async("examples/demos/multi-turn/graph.yaml")
config = {"configurable": {"thread_id": "session-123"}}

# Turn 1: hits interrupt immediately
result = await run_graph_async(app, {"user_message": ""}, config)
# result contains __interrupt__

# Turn 2: resume with user message
result = await run_graph_async(app, Command(resume="hello"), config)
print(result["response"])  # LLM response
# result contains __interrupt__ for next turn

# Turn 3: continue conversation
result = await run_graph_async(app, Command(resume="tell me more"), config)
```

### Guard Classification Pattern

Guard classification runs as a **separate graph call** before the main flow:

```python
from yamlgraph.graph_loader import load_and_compile

# Step 1: Classify intent
guard = load_and_compile("examples/demos/multi-turn/guard.yaml").compile()
intent_result = await guard.ainvoke({"user_message": user_input})
intent = intent_result["intent"]

# Step 2: Route based on intent
if "stop" in intent.lower():
    # Handle stop/goodbye
    return {"response": "Goodbye!"}
else:
    # Continue with main multi-turn flow
    result = await run_graph_async(app, Command(resume=user_input), config)
```

This two-step pattern keeps the guard fast (separate model, no checkpointing) while main flow handles state.

## CLI Usage

```bash
# Validate graphs
yamlgraph graph lint examples/demos/multi-turn/graph.yaml
yamlgraph graph lint examples/demos/multi-turn/guard.yaml

# Test guard classification
yamlgraph graph run examples/demos/multi-turn/guard.yaml \
  --var user_message="stop"

yamlgraph graph run examples/demos/multi-turn/guard.yaml \
  --var user_message="tell me a joke"
```

## Streaming

For multi-turn streaming with memory checkpointer, reuse the compiled app instance:

```python
from yamlgraph.executor_async import load_and_compile_async
from langgraph.types import Command

# Load once, reuse for all turns (memory checkpointer requires same instance)
app = await load_and_compile_async("examples/demos/multi-turn/graph.yaml")
config = {"configurable": {"thread_id": "session-123"}}

# Turn 1: hits interrupt immediately (no streaming before first response)
async for event in app.astream({"user_message": ""}, config, stream_mode="messages"):
    chunk, meta = event
    if hasattr(chunk, "content") and chunk.content:
        print(chunk.content, end="", flush=True)

# Turn 2: resume → respond → interrupt (streams LLM output)
async for event in app.astream(Command(resume="tell me a joke"), config, stream_mode="messages"):
    chunk, meta = event
    if hasattr(chunk, "content") and chunk.content:
        print(chunk.content, end="", flush=True)
```

**Note:** Memory checkpointer state is lost when the app instance is recreated. For persistent multi-turn across requests, use `sqlite` checkpointer:

```yaml
checkpointer:
  type: sqlite
  path: /tmp/multi-turn.db
```

## Files

- `graph.yaml` — Multi-turn conversation graph with interrupt loop
- `guard.yaml` — Fast intent classification graph
- `prompts/respond.yaml` — Main conversation prompt
- `prompts/classify_intent.yaml` — Guard classification prompt
- `prompts/farewell.yaml` — Goodbye response (for guard redirect)

