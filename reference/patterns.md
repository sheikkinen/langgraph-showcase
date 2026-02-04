# Common Patterns

This document showcases common patterns for building pipelines with the YAML-based graph system.

---

## Pattern 1: Linear Pipeline

Simple sequential processing with dependencies.

### Use Case
Content generation → analysis → summarization

### Graph Structure

```yaml
version: "1.0"
name: linear-pipeline

nodes:
  step1:
    type: llm
    prompt: step1
    state_key: step1_output

  step2:
    type: llm
    prompt: step2
    variables:
      input: "{state.step1_output.field}"
    state_key: step2_output
    requires: [step1_output]      # Explicit dependency

  step3:
    type: llm
    prompt: step3
    variables:
      data: "{state.step2_output}"
    state_key: final
    requires: [step1_output, step2_output]

edges:
  - from: START
    to: step1
  - from: step1
    to: step2
  - from: step2
    to: step3
  - from: step3
    to: END
```

### Key Points

- Use `requires` to enforce dependencies
- Use `state_key` to name outputs clearly
- Access nested fields: `{state.output.field}`

---

## Pattern 2: Conditional Routing

Route to different nodes based on LLM classification.

### Use Case
Customer support: route based on inquiry type or sentiment

### Graph Structure

```yaml
version: "1.0"
name: router-pattern

nodes:
  classify:
    type: router
    prompt: classify
    routes:
      type_a: handle_a
      type_b: handle_b
      type_c: handle_c
    default_route: handle_default
    variables:
      input: "{state.input}"
    state_key: classification

  handle_a:
    type: llm
    prompt: handler_a
    variables:
      input: "{state.input}"
    state_key: response

  handle_b:
    type: llm
    prompt: handler_b
    variables:
      input: "{state.input}"
    state_key: response

  handle_c:
    type: llm
    prompt: handler_c
    variables:
      input: "{state.input}"
    state_key: response

  handle_default:
    type: llm
    prompt: handler_default
    variables:
      input: "{state.input}"
    state_key: response

edges:
  - from: START
    to: classify
  - from: classify
    to: [handle_a, handle_b, handle_c, handle_default]
    type: conditional
  - from: handle_a
    to: END
  - from: handle_b
    to: END
  - from: handle_c
    to: END
  - from: handle_default
    to: END
```

### Router Prompt Pattern

```yaml
# prompts/classify.yaml
schema:
  name: Classification
  fields:
    category:
      type: str
      description: "Category: type_a, type_b, or type_c"
    confidence:
      type: float
      constraints:
        ge: 0.0
        le: 1.0

system: |
  Classify the input into one of these categories:
  - type_a: [description]
  - type_b: [description]
  - type_c: [description]

user: |
  Classify: {input}
```

### Key Points

- Router `routes` maps classification values → node names
- Use `default_route` for fallback
- All target nodes must be listed in conditional edge `to: [...]`

---

## Pattern 3: Self-Correction Loop (Reflexion)

Iterative refinement until quality threshold is met.

### Use Case
Essay writing, code generation with quality checks

### Graph Structure

```yaml
version: "1.0"
name: reflexion-pattern

nodes:
  draft:
    type: llm
    prompt: draft
    variables:
      topic: "{state.topic}"
    state_key: current_draft

  critique:
    type: llm
    prompt: critique
    variables:
      content: "{state.current_draft.content}"
      iteration: "{state._loop_counts.critique}"   # Track iteration
    state_key: critique
    skip_if_exists: false    # CRITICAL: Re-run each loop

  refine:
    type: llm
    prompt: refine
    variables:
      content: "{state.current_draft.content}"
      feedback: "{state.critique.feedback}"
    state_key: current_draft   # Overwrites draft
    skip_if_exists: false      # CRITICAL: Re-run each loop

edges:
  - from: START
    to: draft
  - from: draft
    to: critique
  - from: critique
    to: refine
    condition: critique.score < 0.8    # Continue if low score
  - from: critique
    to: END
    condition: critique.score >= 0.8   # Exit if high score
  - from: refine
    to: critique                       # Loop back

loop_limits:
  critique: 5                          # Prevent infinite loops
```

### Critical Configuration

| Setting | Value | Why |
|---------|-------|-----|
| `skip_if_exists` | `false` | Nodes must re-run each iteration |
| `loop_limits` | Set limit | Prevent infinite loops |
| `_loop_counts` | Access in variables | Track current iteration |

### Critique Prompt Pattern

```yaml
schema:
  name: Critique
  fields:
    score:
      type: float
      description: "Quality score 0.0-1.0 (0.8+ is acceptable)"
      constraints:
        ge: 0.0
        le: 1.0
    feedback:
      type: str
      description: "Specific improvements needed"

system: |
  You are a quality reviewer. Score the content 0.0-1.0.
  Score 0.8+ means it's ready, below 0.8 needs refinement.

user: |
  Review this content (iteration {iteration}):

  {content}
```

---

## Pattern 4: Tool-Using Agent

Agent with shell command tools for research and analysis.

### Use Case
Code analysis, repository inspection, data gathering

### Graph Structure

```yaml
version: "1.0"
name: agent-pattern

tools:
  list_files:
    command: ls -la {directory}
    description: "List files in a directory"
    parse: text

  read_file:
    command: cat {filepath}
    description: "Read contents of a file"
    parse: text

  search_code:
    command: grep -r "{pattern}" {directory}
    description: "Search for pattern in code"
    parse: text

  run_tests:
    command: pytest {test_path} -v
    description: "Run tests and get results"
    parse: text

nodes:
  analyze:
    type: agent
    prompt: analyzer
    tools: [list_files, read_file, search_code, run_tests]
    max_iterations: 10
    state_key: analysis

  report:
    type: llm
    prompt: report
    requires: [analysis]
    variables:
      findings: "{state.analysis}"
    state_key: report

edges:
  - from: START
    to: analyze
  - from: analyze
    to: report
  - from: report
    to: END
```

### Agent Prompt Pattern

```yaml
# prompts/analyzer.yaml
system: |
  You are a code analyst with access to these tools:

  1. **list_files**: List directory contents
     - directory: Path to list

  2. **read_file**: Read a file
     - filepath: Path to the file

  3. **search_code**: Search for patterns
     - pattern: Regex pattern
     - directory: Where to search

  4. **run_tests**: Execute tests
     - test_path: Path to tests

  Your task:
  1. Explore the codebase
  2. Identify patterns and issues
  3. Provide actionable insights

user: |
  Analyze the repository and report on code quality.
```

### Key Points

- Tools are defined at graph level, referenced in nodes
- Use `{param}` placeholders in commands
- Agent decides which tools to call and with what parameters
- Set reasonable `max_iterations` to prevent runaway agents

---

## Pattern 5: Error Recovery

Handle LLM failures gracefully with fallbacks.

### Graph Structure

```yaml
version: "1.0"
name: resilient-pipeline

defaults:
  provider: mistral
  temperature: 0.7

nodes:
  primary:
    type: llm
    prompt: process
    on_error: fallback             # Try fallback on failure
    fallback:
      provider: anthropic          # Use different provider
    state_key: result

  # Alternative: retry with same provider
  retry_example:
    type: llm
    prompt: other_process
    on_error: retry
    max_retries: 3                 # Try up to 3 times
    state_key: other_result

  # Alternative: skip on failure (non-critical)
  optional_step:
    type: llm
    prompt: optional
    on_error: skip                 # Continue without output
    state_key: optional_data

edges:
  - from: START
    to: primary
  - from: primary
    to: retry_example
  - from: retry_example
    to: optional_step
  - from: optional_step
    to: END
```

### Error Handling Options

| `on_error` | Behavior | Use Case |
|------------|----------|----------|
| `fallback` | Try different provider | Primary provider rate limited |
| `retry` | Retry N times | Transient errors |
| `skip` | Continue without output | Optional/non-critical steps |
| `fail` | Stop pipeline | Critical steps |

---

## Pattern 6: Multi-Output to Single Input

Multiple steps feed into one consolidation step.

### Graph Structure

```yaml
version: "1.0"
name: multi-input

nodes:
  research_a:
    type: llm
    prompt: research_a
    variables:
      topic: "{state.topic}"
    state_key: research_a

  research_b:
    type: llm
    prompt: research_b
    variables:
      topic: "{state.topic}"
    state_key: research_b

  research_c:
    type: llm
    prompt: research_c
    variables:
      topic: "{state.topic}"
    state_key: research_c

  synthesize:
    type: llm
    prompt: synthesize
    variables:
      source_a: "{state.research_a.content}"
      source_b: "{state.research_b.content}"
      source_c: "{state.research_c.content}"
    state_key: synthesis
    requires: [research_a, research_b, research_c]

edges:
  - from: START
    to: research_a
  - from: START
    to: research_b
  - from: START
    to: research_c
  - from: research_a
    to: synthesize
  - from: research_b
    to: synthesize
  - from: research_c
    to: synthesize
  - from: synthesize
    to: END
```

### Key Points

- Multiple edges from START run concurrently (if supported)
- Use `requires` on consolidation node
- Access multiple sources in variables

---

## Pattern 7: Stateful Memory (AgentState)

Maintain conversation history across interactions.

### Graph Structure

```yaml
version: "1.0"
name: memory-pattern

# State auto-generated with messages reducer for agent

nodes:
  chat:
    type: agent
    prompt: chat
    tools: [search, calculate]
    state_key: response
    tool_results_key: _tool_results
    max_iterations: 5

edges:
  - from: START
    to: chat
  - from: chat
    to: END

exports:
  response:
    format: markdown
    filename: chat.md
  _tool_results:
    format: json
    filename: tool_log.json
```

### AgentState Definition

```python
# yamlgraph/models/state.py
from langgraph.graph.message import add_messages

class AgentState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]  # Accumulates messages
    response: str
    _tool_results: list[dict]
```

---

## Pattern 8: Parallel Fan-Out (Map)

Process each item in a list in parallel and collect results.

### Use Case
- Transform multiple documents/panels/items simultaneously
- Generate images for each story panel
- Analyze multiple code files in parallel

### Graph Structure

```yaml
version: "1.0"
name: map-pattern

state:
  items: list
  processed_items: list

nodes:
  generate_items:
    type: llm
    prompt: generate_items
    state_key: items              # Returns a list

  process_items:
    type: map
    over: "{state.items}"         # List to iterate
    as: item                      # Variable name per item
    node:
      type: llm
      prompt: process_item
      state_key: processed_item
    collect: processed_items      # Collected results

  summarize:
    type: llm
    prompt: summarize
    variables:
      results: "{state.processed_items}"
    state_key: summary
    requires: [processed_items]

edges:
  - from: START
    to: generate_items
  - from: generate_items
    to: process_items
  - from: process_items
    to: summarize
  - from: summarize
    to: END
```

### Sub-Node Prompt Pattern

```yaml
# prompts/process_item.yaml
schema:
  name: ProcessedItem
  fields:
    result:
      type: str
      description: "Processed output"
    metadata:
      type: dict
      description: "Additional info"

system: |
  Process the given item and return structured output.

user: |
  Process this item: {item}
```

### Real-World Example: Animated Storyboard

```yaml
nodes:
  expand_story:
    type: llm
    prompt: expand_story
    state_key: story              # {title, panels: [...]}

  animate_panels:
    type: map
    over: "{state.story.panels}"  # List of panel descriptions
    as: panel_prompt
    node:
      type: llm
      prompt: animate_panel       # Convert to first/middle/last frames
      state_key: animated_panel
    collect: animated_panels

  generate_images:
    type: python
    tool: generate_images
    requires: [animated_panels]

edges:
  - from: START
    to: expand_story
  - from: expand_story
    to: animate_panels
  - from: animate_panels
    to: generate_images
  - from: generate_images
    to: END
```

### Key Points

- Use `type: map` for parallel list processing
- `over` specifies the list to iterate (supports nested access)
- `as` defines the variable name available in sub-node
- `collect` aggregates all results into a list
- Results include `_map_index` for ordering
- Sub-nodes can be `llm`, `router`, or `python` type

See [Map Nodes Reference](map-nodes.md) for comprehensive documentation.

---

## Cheat Sheet

### Node Type Quick Reference

| Type | Purpose | Required Fields |
|------|---------|-----------------|
| `llm` | LLM call with optional structured output | `prompt` |
| `router` | Classification → routing | `prompt`, `routes` |
| `map` | Parallel fan-out over lists | `over`, `as`, `node`, `collect` |
| `python` | Custom Python function | `tool` |
| `agent` | Tool-using autonomous agent | `prompt`, `tools` |

### Common Variable Patterns

```yaml
variables:
  # Simple state access
  topic: "{state.topic}"

  # Nested object access
  content: "{state.generated.content}"

  # Loop counter
  iteration: "{state._loop_counts.node_name}"

  # List (auto-joined with ", ")
  tags: "{state.analysis.tags}"
```

### Edge Condition Patterns

```yaml
edges:
  # Simple linear
  - from: a
    to: b

  # Terminal
  - from: b
    to: END

  # Router conditional
  - from: classify
    to: [opt_a, opt_b, opt_c]
    type: conditional

  # Expression-based
  - from: critique
    to: refine
    condition: critique.score < 0.8
```

---

## Pattern 9: Soul Pattern (Agent Personality)

Give AI agents consistent personality using `data_files` to load a soul configuration.

### Use Case
- Customer service agents with brand-appropriate tone
- Multiple personality variants (friendly, formal, technical)
- A/B testing different communication styles

### Soul File Structure

```yaml
# souls/friendly.yaml
name: Friendly Helper

voice: warm, approachable, patient, and encouraging

principles:
  - Always acknowledge the person's situation before providing solutions
  - Use "we" language to create a sense of partnership
  - Explain technical concepts with everyday analogies
  - End responses with clear, actionable next steps

constraints:
  - Never blame the user for problems
  - Avoid jargon unless the user uses it first
  - Don't be condescending or overly simplistic
```

### Graph Configuration

```yaml
version: "1.0"
name: personality-agent

# Soul loaded via data_files - available as {{ soul }} in all prompts
data_files:
  soul: souls/friendly.yaml

nodes:
  respond:
    type: llm
    prompt: respond
    state_key: response
```

### Prompt Template

```yaml
# prompts/respond.yaml
system: |
  You are {{ soul.name }}.
  Your communication style is: {{ soul.voice }}

  Core principles:
  {% for principle in soul.principles %}
  - {{ principle }}
  {% endfor %}

  Things to avoid:
  {% for constraint in soul.constraints %}
  - {{ constraint }}
  {% endfor %}

user: |
  {{ message }}
```

### Switching Souls

Three ways to use different personalities:

| Method | When to Use |
|--------|-------------|
| Change `data_files.soul` path | Different builds/deployments |
| Pass `soul` as input | Runtime override (input wins) |
| Different graph files | Distinct product variants |

### Runtime Override Example

```bash
# Override soul at runtime via CLI
yamlgraph run graph.yaml \
  --var 'message=Hello!' \
  --var 'soul={"name": "Quick Bot", "voice": "brief", "principles": ["be fast"]}'
```

### Example

See [examples/soul](../examples/soul/) for a complete working example.
