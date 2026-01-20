# Passthrough Nodes

Passthrough nodes transform state without making external calls. They're useful for:
- Loop counters
- State accumulation
- Simple data transformations
- Clean transition points in graphs

## Basic Usage

```yaml
nodes:
  increment_counter:
    type: passthrough
    output:
      counter: "{state.counter + 1}"
```

## Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"passthrough"` | ✅ | Node type identifier |
| `output` | `dict` | ✅ | Map of state keys to expressions |

## Expression Syntax

Expressions use the standard `{state.field}` syntax with support for:

### Arithmetic
```yaml
output:
  turn_number: "{state.turn_number + 1}"
  total: "{state.a + state.b}"
  scaled: "{state.value * 2}"
```

### List Operations
```yaml
output:
  # Append single item
  history: "{state.history + [state.current_item]}"

  # Append dict
  log: "{state.log + [{'turn': state.turn, 'action': state.action}]}"
```

### String Operations
```yaml
output:
  message: "{state.prefix + ': ' + state.content}"
```

### Conditional (Python expressions)
```yaml
output:
  status: "{'complete' if state.count >= 10 else 'in_progress'}"
```

## Examples

### Loop Counter

```yaml
version: "1.0"
name: loop-example

state:
  counter: int
  max_iterations: int
  result: str

nodes:
  process:
    type: llm
    prompt: process
    state_key: result
    skip_if_exists: false

  next_iteration:
    type: passthrough
    output:
      counter: "{state.counter + 1}"

edges:
  - from: START
    to: process
  - from: process
    to: next_iteration
  - from: next_iteration
    to: process
    condition: "counter < max_iterations"
  - from: next_iteration
    to: END
    condition: "counter >= max_iterations"
```

### History Accumulation

```yaml
version: "1.0"
name: conversation-loop

state:
  messages: list
  current_message: str
  response: str

nodes:
  respond:
    type: llm
    prompt: chat
    state_key: response
    skip_if_exists: false

  save_history:
    type: passthrough
    output:
      messages: "{state.messages + [{'user': state.current_message, 'assistant': state.response}]}"

edges:
  - from: START
    to: respond
  - from: respond
    to: save_history
  - from: save_history
    to: END
```

### Multi-Turn Game Loop

```yaml
version: "1.0"
name: game-turn

checkpointer:
  type: sqlite
  path: ":memory:"

state:
  turn_number: int
  player_input: str
  game_state: dict
  turn_log: list

nodes:
  await_input:
    type: interrupt
    message: "Your move:"
    resume_key: player_input

  process_turn:
    type: llm
    prompt: game/process_turn
    state_key: game_state
    skip_if_exists: false

  log_turn:
    type: passthrough
    output:
      turn_number: "{state.turn_number + 1}"
      turn_log: "{state.turn_log + [{'turn': state.turn_number, 'input': state.player_input, 'result': state.game_state}]}"

edges:
  - from: START
    to: await_input
  - from: await_input
    to: END
    condition: "player_input == 'quit'"
  - from: await_input
    to: process_turn
    condition: "player_input != 'quit'"
  - from: process_turn
    to: log_turn
  - from: log_turn
    to: await_input
```

## Error Handling

If an expression fails to resolve, the passthrough node:
1. Logs a warning
2. Keeps the original value (if the key exists in state)
3. Continues execution

This prevents loops from breaking on transient errors.

## Best Practices

1. **Use for simple transformations** - Complex logic should use `type: python`
2. **Always set `skip_if_exists: false`** on LLM nodes in loops
3. **Initialize state** - Ensure list fields start as `[]` not `null`
4. **Test expressions** - Validate arithmetic/list operations work as expected

## Related

- [Graph YAML Reference](graph-yaml.md) - Full graph configuration
- [Interrupt Nodes](patterns.md#human-in-the-loop) - Human input in loops
- [Expressions](patterns.md#expressions) - Template syntax
