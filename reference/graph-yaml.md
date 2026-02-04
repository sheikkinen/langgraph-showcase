# Graph YAML Reference

This document explains all configuration options for graph YAML files. Graphs are typically located in `examples/demos/*/graph.yaml` or your project's graph directory.

## File Structure

```yaml
version: "1.0"                    # Schema version
name: my-pipeline                  # Graph identifier
description: What this graph does  # Human-readable description

defaults:                          # Default values for all nodes
  provider: mistral
  temperature: 0.7

data_files:                        # Optional: Load external YAML into state
  schema: schema.yaml

tools:                             # Optional: Tool definitions for agents
  tool_name: { ... }

nodes:                             # Required: Node definitions
  node_name: { ... }

edges:                             # Required: Edge definitions
  - from: START
    to: node_name

loop_limits:                       # Optional: Max iterations per node
  node_name: 3

exports:                           # Optional: Export configuration
  state_key:
    format: markdown
    filename: output.md
```

---

## Top-Level Properties

### `version`
**Type:** `string`
**Default:** `"1.0"`

Schema version for the YAML format.

```yaml
version: "1.0"
```

### `name`
**Type:** `string`
**Default:** `"unnamed"`

Identifier for the graph, used in logging and display.

```yaml
name: content-pipeline
```

### `description`
**Type:** `string`
**Default:** `""`

Human-readable description of what the graph does.

```yaml
description: Content generation pipeline (generate → analyze → summarize)
```

### `defaults`
**Type:** `object`

Default configuration applied to all nodes unless overridden.

```yaml
defaults:
  provider: mistral       # Default LLM provider
  temperature: 0.7        # Default temperature
  prompts_relative: true  # Resolve prompts relative to graph file
  prompts_dir: path/to   # Explicit prompts directory (optional)
```

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `provider` | `string` | env-based | Default LLM provider |
| `temperature` | `float` | `0.7` | Default temperature |
| `prompts_relative` | `bool` | `false` | Resolve prompts relative to graph file |
| `prompts_dir` | `string` | `prompts/` | Explicit prompts directory path |

**Prompt Resolution Order:**
1. If `prompts_dir` specified: `{prompts_dir}/{prompt_name}.yaml`
2. If `prompts_relative: true`: `{graph_dir}/{prompt_name}.yaml`
3. Default: `prompts/{prompt_name}.yaml`

**Example - Colocated prompts:**
```
questionnaires/
  audit/
    graph.yaml              # prompts_relative: true
    prompts/
      opening.yaml
      extract.yaml
  phq9/
    graph.yaml
    prompts/
      opening.yaml
```

```yaml
# questionnaires/audit/graph.yaml
defaults:
  prompts_relative: true

nodes:
  generate_opening:
    type: llm
    prompt: prompts/opening  # → questionnaires/audit/prompts/opening.yaml
```

---

### `data_files`
**Type:** `object`
**Default:** `{}`

Load external YAML files into graph state at compile time. Useful for:
- Schema definitions shared across prompts
- Configuration data (personas, categories, rules)
- Reference data that doesn't change between runs

```yaml
data_files:
  schema: schema.yaml           # Load as state.schema
  personas: data/personas.yaml  # Load as state.personas
```

**Paths are relative to the graph file**, not the working directory. This ensures portability.

**Security:** Path traversal (`../`) is blocked. Data files must be within the graph directory.

**Example - Survey with shared schema:**

```
surveys/
  satisfaction/
    graph.yaml
    schema.yaml        # Field definitions
    prompts/
      extract.yaml
```

```yaml
# surveys/satisfaction/graph.yaml
version: "1.0"
name: satisfaction-survey

data_files:
  schema: schema.yaml   # Loaded at compile time

nodes:
  extract:
    type: llm
    prompt: prompts/extract
    variables:
      fields: "{state.schema.fields}"  # Access loaded data
```

```yaml
# surveys/satisfaction/schema.yaml
fields:
  - name: satisfaction_score
    type: int
    range: [1, 10]
  - name: feedback
    type: str
    required: false
```

**Empty files** return `{}` (empty dict), not `null`.

**State collision:** If input provides a key that matches a `data_files` key, the input value wins.

---

## Node Definition

Each node in the `nodes` section defines a processing step.

### Common Node Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `type` | `string` | `"llm"` | Node type: `llm`, `router`, `agent`, `python`, `map`, `interrupt`, `passthrough`, `tool_call`, `subgraph` |
| `prompt` | `string` | varies | Prompt file path (without `.yaml`) |
| `variables` | `object` | `{}` | Template variable mappings |
| `state_key` | `string` | node name | State key to store result |
| `requires` | `list[str]` | `[]` | Required state keys before execution |
| `temperature` | `float` | from defaults | LLM temperature |
| `provider` | `string` | from defaults | LLM provider |
| `skip_if_exists` | `bool` | `true` | Skip if output already in state |
| `parse_json` | `bool` | `false` | Extract JSON from LLM response |
| `stream` | `bool` | `false` | Enable token-by-token streaming |

### `type: llm` - Standard LLM Node

Basic LLM execution with structured output.

```yaml
nodes:
  generate:
    type: llm
    prompt: generate                 # prompts/generate.yaml
    temperature: 0.8
    variables:
      topic: "{state.topic}"
      word_count: "{state.word_count}"
    state_key: generated
    requires: []                     # No dependencies
```

**JSON Extraction:**

When LLMs wrap JSON in markdown code blocks, use `parse_json: true`:

```yaml
nodes:
  extract_fields:
    type: llm
    prompt: extract
    state_key: extracted
    parse_json: true                 # Auto-extract JSON from response
```

This extracts JSON from responses like:
```
```json
{"name": "test", "value": 42}
```

Reasoning: I extracted the structured data...
```

The node stores the parsed dict `{"name": "test", "value": 42}` instead of raw string.

**Streaming:**

For token-by-token output (useful in web UIs):

```yaml
nodes:
  generate_story:
    type: llm
    prompt: story
    stream: true                     # Enable streaming
```
    type: llm
    prompt: generate                 # prompts/generate.yaml
    temperature: 0.8
    variables:
      topic: "{state.topic}"
      word_count: "{state.word_count}"
    state_key: generated
    requires: []                     # No dependencies
```

### `type: router` - Conditional Routing

Routes to different nodes based on LLM classification.

```yaml
nodes:
  classify:
    type: router
    prompt: router-demo/classify_tone
    routes:                          # Maps classification → node
      positive: respond_positive
      negative: respond_negative
      neutral: respond_neutral
    default_route: respond_neutral   # Fallback if no match
    variables:
      message: "{state.message}"
    state_key: classification
```

**Required properties for routers:**
- `routes`: Map of classification values to target nodes
- Prompt must return an object with `tone`, `intent`, or similar field

### `type: agent` - Tool-Using Agent

Agent with access to tools for multi-step reasoning.

```yaml
nodes:
  analyze:
    type: agent
    prompt: git_analyst
    tools: [recent_commits, commit_details]  # Tools from graph's tools section
    max_iterations: 8                         # Max tool calls
    state_key: analysis
```

**Agent-specific properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `tools` | `list[str]` | `[]` | Tool names from graph's `tools` section |
| `max_iterations` | `int` | `5` | Maximum tool invocations |
| `tool_results_key` | `string` | - | State key for tool execution logs |

### `type: python` - Python Function Node

Execute an arbitrary Python function as a node.

```yaml
nodes:
  generate_images:
    type: python
    tool: generate_images            # References tool from tools section
    state_key: images
    requires: [story]                # Wait for story to be generated
```

**Python node properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `tool` | `string` | required | Name of Python tool from `tools` section |
| `state_key` | `string` | node name | State key to store result |
| `requires` | `list[str]` | `[]` | Required state keys before execution |
| `on_error` | `string` | `"fail"` | Error handling: `skip` or `fail` |

**Note:** The Python function must be defined in the `tools` section with `type: python`.

### `type: map` - Parallel Fan-Out Node

Process each item in a list in parallel using LangGraph's `Send()` API.

```yaml
nodes:
  animate_panels:
    type: map
    over: "{state.story.panels}"     # List to iterate over
    as: panel_prompt                  # Variable name for each item
    node:                             # Sub-node executed per item
      type: llm
      prompt: animate_panel
      state_key: animated_panel
    collect: animated_panels          # State key for collected results
```

**Map node properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `over` | `string` | Yes | State expression for the list to iterate |
| `as` | `string` | Yes | Variable name injected into sub-node |
| `node` | `object` | Yes | Sub-node definition (llm, router, or python) |
| `collect` | `string` | Yes | State key where results are collected |

**How it works:**
1. Fan-out: Each item is dispatched via `Send()` for parallel processing
2. Process: Sub-node runs independently per item with `{state.<as>}` available
3. Collect: Results are aggregated using `Annotated[list, operator.add]` reducer

**Sub-node variable access:**
```yaml
as: panel_prompt
node:
  type: llm
  prompt: animate_panel
  variables:
    prompt: "{state.panel_prompt}"    # Access injected item
    context: "{state.story.title}"    # Access parent state
```

See [Map Nodes Reference](map-nodes.md) for detailed examples and patterns.

### `type: interrupt` - Human-in-the-Loop

Pause execution to wait for human input. Requires a checkpointer.

```yaml
checkpointer:
  type: memory

nodes:
  ask_name:
    type: interrupt
    message: "What is your name?"
    resume_key: user_name
```

**Interrupt node properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `message` | `string/dict` | Yes* | Static interrupt payload |
| `prompt` | `string` | Yes* | Prompt name for dynamic payload |
| `state_key` | `string` | No | Where to store payload (default: `interrupt_message`) |
| `resume_key` | `string` | No | Where to store resume value (default: `user_input`) |

*Either `message` or `prompt` required.

See [Interrupt Nodes Reference](interrupt-nodes.md) for resume flow and Python API.

### `type: passthrough` - State Transformation

Transform state without external calls. Useful for counters and accumulators.

```yaml
nodes:
  increment_turn:
    type: passthrough
    output:
      turn_number: "{state.turn_number + 1}"
      history: "{state.history + [state.current_action]}"
```

**Passthrough node properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `output` | `dict` | Yes | Map of state keys to expressions |

Supports arithmetic, list operations, and conditionals.

See [Passthrough Nodes Reference](passthrough-nodes.md) for expression syntax.

### `type: tool_call` - Dynamic Tool Execution

Execute a tool where name and arguments come from state (LLM-driven orchestration).

```yaml
nodes:
  execute_tool:
    type: tool_call
    tool_name: "{state.selected_tool}"
    tool_args: "{state.tool_arguments}"
    state_key: tool_result
```

**Tool call node properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `tool_name` | `string` | Yes | State expression resolving to tool name |
| `tool_args` | `string` | Yes | State expression resolving to args dict |
| `state_key` | `string` | No | Where to store result |

See [Tool Call Nodes Reference](tool-call-nodes.md) for agent integration patterns.

### `type: subgraph` - Nested Graph

Embed and execute another graph as a node. Enables modular composition.

```yaml
nodes:
  summarize:
    type: subgraph
    mode: invoke
    graph: subgraphs/summarizer.yaml
    input_mapping:
      prepared_text: input_text      # parent → child
    output_mapping:
      summary: output_summary        # child → parent
```

**Subgraph node properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `graph` | `string` | Yes | Path to child graph YAML |
| `mode` | `string` | No | `invoke` (default) or `stream` |
| `input_mapping` | `dict` | No | Map parent state keys to child state keys |
| `output_mapping` | `dict` | No | Map child state keys to parent state keys |

See [Subgraph Nodes Reference](subgraph-nodes.md) for state mapping patterns and nesting.

### Error Handling Properties

All node types support error handling:

```yaml
nodes:
  generate:
    type: llm
    prompt: generate
    on_error: fallback               # skip | retry | fail | fallback
    max_retries: 3                   # For retry mode
    fallback:
      provider: anthropic            # Fallback provider for fallback mode
```

| `on_error` Value | Behavior |
|------------------|----------|
| `skip` | Log warning, continue without output |
| `retry` | Retry up to `max_retries` times |
| `fail` | Raise exception, halt pipeline |
| `fallback` | Try `fallback.provider` on failure |

---

## Variable Templates

The `variables` section maps prompt variables to state values.

### Syntax

```yaml
variables:
  simple: "{state.field}"              # Direct field access
  nested: "{state.obj.attr}"           # Nested object access
  loop: "{state._loop_counts.node}"    # Access loop counter
```

### Resolution

Templates are resolved at runtime by `node_factory.resolve_template()`:

1. `{state.field}` → `state.get("field")`
2. `{state.obj.attr}` → `state.get("obj").attr`
3. Lists are joined with `, ` for simple template placeholders

---

## Edge Definition

Edges define the flow between nodes.

### Linear Edge

Simple node-to-node connection:

```yaml
edges:
  - from: generate
    to: analyze
```

### Entry Point

Start the graph at a node:

```yaml
edges:
  - from: START
    to: generate
```

### Terminal Edge

End the graph after a node:

```yaml
edges:
  - from: summarize
    to: END
```

### Conditional Edge (Router)

For router nodes, specify multiple targets:

```yaml
edges:
  - from: classify
    to: [respond_positive, respond_negative, respond_neutral]
    type: conditional
```

### Expression-Based Conditions

Route based on state values:

```yaml
edges:
  - from: critique
    to: refine
    condition: critique.score < 0.8    # Go to refine if low score

  - from: critique
    to: END
    condition: critique.score >= 0.8   # End if high score
```

**Supported operators:** `<`, `<=`, `>`, `>=`, `==`, `!=`

---

## Security Considerations

### Expression Evaluation Safety

Condition expressions are evaluated **without using `eval()`**. The expression parser only supports:

**Safe operations:**
- Field path resolution: `critique.score`, `result.status`
- Comparison operators: `<`, `<=`, `>`, `>=`, `==`, `!=`
- Compound expressions: `a > 1 and b < 2`, `x == "done" or y == "skip"`
- Literal values: integers, floats, booleans, quoted strings

**Not supported (by design):**
- Arbitrary Python code execution
- Function calls
- Import statements
- Assignment expressions

Example of validated expression parsing:

```python
# Safe - parsed with regex, not eval()
evaluate_condition("critique.score < 0.8", state)  # ✓
evaluate_condition("a > 1 and b == 'done'", state)  # ✓

# Not supported - will fail validation
"__import__('os').system('cmd')"  # ✗ Rejected
```

### Shell Tool Security

Shell commands use `shlex.quote()` for parameter sanitization. See the main README Security section for details.

---

## Tools Definition

Define tools for agent nodes in the `tools` section.

### Shell Tool

Execute shell commands:

```yaml
tools:
  recent_commits:
    type: shell                       # Optional, defaults to shell
    command: git log --oneline -n {count}
    description: "List recent commits"
    parse: text                       # Output format: text | json
```

**Parameterized commands:**
- Use `{param_name}` placeholders in commands
- Agent provides parameter values at runtime

### Python Tool

Execute Python functions directly:

```yaml
tools:
  generate_images:
    type: python
    module: examples.storyboard.nodes.image_node
    function: generate_images_node
    description: "Generate images for each story panel"
```

**Python tool properties:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `type` | `string` | Yes | Must be `"python"` |
| `module` | `string` | Yes | Full Python module path |
| `function` | `string` | Yes | Function name in the module |
| `description` | `string` | No | Human-readable description |

**Function signature:**
The Python function must accept `state: dict[str, Any]` and return a `dict` with state updates:

```python
def generate_images_node(state: dict[str, Any]) -> dict:
    """Process state and return updates."""
    story = state.get("story")
    # ... do work ...
    return {
        "images": image_paths,
        "current_step": "generate_images",
    }
```

### Example Tools

```yaml
tools:
  commit_details:
    command: git show --stat {commit_hash}
    description: "Show details of a specific commit by hash"
    parse: text

  line_count:
    command: wc -l {file} | awk '{print $1}'
    description: "Count lines in a file"
    parse: text
```

### Web Search Tool

Search the web using DuckDuckGo (no API key required):

```yaml
tools:
  search_web:
    type: websearch
    provider: duckduckgo
    max_results: 5
    description: "Search the web for current information"
```

**Web search tool properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `type` | `string` | required | Must be `"websearch"` |
| `provider` | `string` | `"duckduckgo"` | Search provider |
| `max_results` | `int` | `5` | Max results per query |
| `description` | `string` | - | Human-readable description |

**Installation:**
```bash
pip install yamlgraph[websearch]
```

### Tool Type Summary

| Type | Description | Example |
|------|-------------|---------|
| `shell` | Execute shell commands | `git log`, `ruff check` |
| `python` | Call Python functions | Custom processing |
| `websearch` | Web search via DuckDuckGo | Research agents |

---

## Loop Limits

Prevent infinite loops in self-correction patterns:

```yaml
loop_limits:
  critique: 3     # Node 'critique' runs at most 3 times
```

**Note:** Use with `skip_if_exists: false` on loop nodes.

---

## Exports

Configure automatic result export:

```yaml
exports:
  response:
    format: markdown
    filename: review.md

  _tool_results:
    format: json
    filename: tool_outputs.json
```

**Supported formats:** `markdown`, `json`, `text`

---

## Complete Examples

### Linear Pipeline

```yaml
version: "1.0"
name: yamlgraph

nodes:
  generate:
    type: llm
    prompt: generate
    variables:
      topic: "{state.topic}"
    state_key: generated

  analyze:
    type: llm
    prompt: analyze
    variables:
      content: "{state.generated.content}"
    state_key: analysis
    requires: [generated]

edges:
  - from: START
    to: generate
  - from: generate
    to: analyze
  - from: analyze
    to: END
```

### Self-Correction Loop

```yaml
version: "1.0"
name: reflexion-demo

nodes:
  draft:
    type: llm
    prompt: reflexion-demo/draft
    state_key: current_draft

  critique:
    type: llm
    prompt: reflexion-demo/critique
    variables:
      content: "{state.current_draft.content}"
      iteration: "{state._loop_counts.critique}"
    state_key: critique
    skip_if_exists: false           # Re-run each iteration

  refine:
    type: llm
    prompt: reflexion-demo/refine
    variables:
      content: "{state.current_draft.content}"
      feedback: "{state.critique.feedback}"
    state_key: current_draft
    skip_if_exists: false

edges:
  - from: START
    to: draft
  - from: draft
    to: critique
  - from: critique
    to: refine
    condition: critique.score < 0.8
  - from: critique
    to: END
    condition: critique.score >= 0.8
  - from: refine
    to: critique

loop_limits:
  critique: 3
```

### Router Pattern

```yaml
version: "1.0"
name: router-demo

nodes:
  classify:
    type: router
    prompt: router-demo/classify_tone
    routes:
      positive: respond_positive
      negative: respond_negative
      neutral: respond_neutral
    default_route: respond_neutral
    variables:
      message: "{state.message}"

  respond_positive:
    type: llm
    prompt: router-demo/respond_positive
    variables:
      message: "{state.message}"
    state_key: response

  # ... other response nodes

edges:
  - from: START
    to: classify
  - from: classify
    to: [respond_positive, respond_negative, respond_neutral]
    type: conditional
  - from: respond_positive
    to: END
```
