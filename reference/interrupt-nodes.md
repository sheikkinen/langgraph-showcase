# Interrupt Nodes

Interrupt nodes pause graph execution to wait for human input. They enable human-in-the-loop workflows where the graph needs external data before continuing.

## Quick Start

```yaml
# examples/demos/interview/graph.yaml
version: "1.0"
name: interview

checkpointer:
  type: memory  # Required for interrupts

state:
  user_name: str
  user_topic: str

nodes:
  ask_name:
    type: interrupt
    message: "What is your name?"
    resume_key: user_name

  ask_topic:
    type: interrupt
    prompt: interview/ask_topic  # Dynamic message from LLM
    state_key: topic_question
    resume_key: user_topic

edges:
  - from: START
    to: ask_name
  - from: ask_name
    to: ask_topic
  - from: ask_topic
    to: END
```

## Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | string | required | Must be `"interrupt"` |
| `message` | string/dict | - | Static interrupt payload |
| `prompt` | string | - | Prompt name for dynamic payload |
| `state_key` | string | `"interrupt_message"` | Where to store the payload |
| `resume_key` | string | `"user_input"` | Where to store resume value |

Either `message` or `prompt` should be specified (not both).

## How It Works

1. **First run**: Node executes, stores payload in `state_key`, then pauses
2. **Result**: Graph returns with `__interrupt__` containing the payload
3. **Resume**: Call with `Command(resume=value)` to continue
4. **Second run**: Node retrieves stored payload (idempotent), returns resume value in `resume_key`

## Usage

### Python API

```python
from langgraph.types import Command
from yamlgraph.graph_loader import load_and_compile, get_checkpointer_for_graph

# Load graph
config = load_graph_config("examples/demos/interview/graph.yaml")
graph = compile_graph(config)
checkpointer = get_checkpointer_for_graph(config)
app = graph.compile(checkpointer=checkpointer)

# Run with thread_id (required for checkpointing)
thread_config = {"configurable": {"thread_id": "session-123"}}
result = app.invoke({"input": "start"}, thread_config)

# Check for interrupt
if "__interrupt__" in result:
    question = result["__interrupt__"][0].value
    print(f"Question: {question}")

    # Get user input
    answer = input("> ")

    # Resume
    result = app.invoke(Command(resume=answer), thread_config)
```

### Async API

```python
from yamlgraph.executor_async import load_and_compile_async, run_graph_async

app = await load_and_compile_async("examples/demos/interview/graph.yaml")
config = {"configurable": {"thread_id": "session-123"}}

result = await run_graph_async(app, {"input": "start"}, config)

if "__interrupt__" in result:
    answer = await get_user_input()  # Your async input method
    result = await run_graph_async(app, Command(resume=answer), config)
```

## Dynamic Prompts

Generate interrupt messages using LLM:

```yaml
nodes:
  ask_topic:
    type: interrupt
    prompt: interview/ask_topic  # Uses prompts/interview/ask_topic.yaml
    state_key: topic_question
    resume_key: user_topic
```

The prompt can access state variables:

```yaml
# prompts/interview/ask_topic.yaml
system: Generate a friendly question asking about interests.
user: |
  The user's name is {user_name}.
  Ask them what topic they'd like to learn about.
```

## Idempotency

⚠️ **Important**: LangGraph re-runs the entire node when resuming. The interrupt node implementation handles this by:

1. Checking if `state_key` already exists in state
2. If yes, skipping prompt execution (using stored payload)
3. If no, executing prompt and storing result

This ensures prompts are only executed once, not on every resume.

## Requirements

- **Checkpointer**: Interrupt nodes require a checkpointer for state persistence
- **Thread ID**: Each session needs a unique `thread_id` in config

## See Also

- [Checkpointers](checkpointers.md) - Configure state persistence
- [Async Usage](async-usage.md) - Async graph execution
- [Graph YAML](graph-yaml.md) - Full graph configuration reference
