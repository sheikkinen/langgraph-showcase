# Map Nodes Reference

Map nodes enable parallel processing of list items using LangGraph's native `Send` API. Each item in a list is processed independently, and results are automatically collected into a list.

---

## Overview

Map nodes solve the fan-out/fan-in pattern:

```
[item1, item2, item3]  →  process each  →  [result1, result2, result3]
```

**Key features:**
- Parallel execution via LangGraph `Send()`
- Automatic result collection with state reducers
- Supports nested LLM, router, or python sub-nodes
- Full access to parent state in sub-nodes

---

## Basic Syntax

```yaml
nodes:
  process_items:
    type: map
    over: "{state.items}"           # List to iterate
    as: item                        # Variable name for each item
    node:                           # Sub-node to execute per item
      type: llm
      prompt: process_item
      state_key: processed_item
    collect: processed_items        # State key for collected results
```

---

## Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `type` | `string` | Yes | Must be `"map"` |
| `over` | `string` | Yes | State expression for the list to iterate |
| `as` | `string` | Yes | Variable name injected into sub-node |
| `node` | `object` | Yes | Sub-node definition (llm, router, or python) |
| `collect` | `string` | Yes | State key where results are collected |

### `over` Expression

Supports nested object access:

```yaml
over: "{state.story.panels}"        # Access nested field
over: "{state.items}"               # Simple list
over: "{state.analysis.key_points}" # Any list in state
```

### `as` Variable

The `as` variable is automatically injected into the sub-node's variables:

```yaml
as: panel                           # Each panel becomes {state.panel}
```

Inside the sub-node, access via `{state.panel}` or `{state.panel.field}`.

### Sub-Node Types

Map nodes support these sub-node types:

| Type | Use Case |
|------|----------|
| `llm` | Transform each item with LLM |
| `router` | Classify/route each item |
| `python` | Custom processing per item |

---

## How It Works

1. **Fan-out**: Graph loader creates a conditional edge that uses `Send()` to dispatch each item
2. **Processing**: Sub-node runs independently for each item with the item injected into state
3. **Collection**: Results are collected using a state reducer (`Annotated[list, operator.add]`)

### State Reducer

The `collect` key automatically gets a list reducer:

```python
# Auto-generated state
class State(TypedDict):
    processed_items: Annotated[list, operator.add]  # Reducer for collection
```

---

## Examples

### Example 1: Animate Story Panels

Transform each panel description into animation frames:

```yaml
# graphs/animated-storyboard.yaml
nodes:
  expand_story:
    type: llm
    prompt: expand_story
    state_key: story              # Returns {panels: [...]}

  animate_panels:
    type: map
    over: "{state.story.panels}"  # List of panel descriptions
    as: panel_prompt
    node:
      type: llm
      prompt: animate_panel
      state_key: animated_panel   # Each iteration produces this
    collect: animated_panels      # All results collected here

edges:
  - from: START
    to: expand_story
  - from: expand_story
    to: animate_panels
  - from: animate_panels
    to: END
```

**Prompt** (`prompts/animate_panel.yaml`):

```yaml
schema:
  name: AnimatedPanel
  fields:
    first_frame:
      type: str
      description: "Opening frame of the animation"
    original:
      type: str
      description: "Middle frame (original panel)"
    last_frame:
      type: str
      description: "Closing frame of the animation"

system: |
  You are an animator. Given a static panel description,
  create three frames showing motion progression.

user: |
  Create animation frames for this panel:
  {panel_prompt}
```

### Example 2: Process with Python Node

Use a custom Python function for each item:

```yaml
nodes:
  generate_images:
    type: map
    over: "{state.animated_panels}"
    as: panel
    node:
      type: python
      tool: generate_panel_image    # References tools section
      state_key: image_result
    collect: images

tools:
  generate_panel_image:
    type: python
    module: myproject.nodes.image_gen
    function: generate_image
```

### Example 3: Classify Each Item

Route each item through classification:

```yaml
nodes:
  classify_items:
    type: map
    over: "{state.items}"
    as: item
    node:
      type: router
      prompt: classify_item
      routes:
        urgent: handle_urgent
        normal: handle_normal
      default_route: handle_normal
    collect: classifications
```

---

## Full Working Example

Complete animated storyboard with character consistency:

```yaml
# examples/storyboard/animated-character-graph.yaml
name: animated-character-storyboard
version: "1.0"

state:
  concept: str
  model: str
  story: any
  animated_panels: list
  character_image: str

tools:
  generate_animated_character_images:
    type: python
    module: examples.storyboard.nodes.animated_character_node
    function: generate_animated_character_images

nodes:
  expand_story:
    type: llm
    prompt: examples/storyboard/expand_character_story
    state_key: story
    variables:
      concept: "{state.concept}"

  animate_panels:
    type: map
    over: "{state.story.panels}"
    as: panel_prompt
    node:
      type: llm
      prompt: examples/storyboard/animate_character_panel
      state_key: animated_panel
    collect: animated_panels

  generate_images:
    type: python
    tool: generate_animated_character_images
    state_key: images
    requires: [animated_panels, story]

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

**Run it:**

```bash
yamlgraph graph run examples/storyboard/animated-character-graph.yaml \
  --var concept="A brave mouse knight on an adventure" \
  --var model=hidream
```

---

## Implementation Details

### Generated Node Structure

For a map node named `animate_panels`, the loader creates:

1. **Dispatch node** (`animate_panels`): Reads the list and sends items
2. **Sub-node** (`_map_animate_panels_sub`): Processes each item
3. **Conditional edge**: Routes from dispatch to sub-node via `Send()`

### State During Execution

Each sub-node execution receives:

```python
{
    # Full parent state
    "story": {...},
    "concept": "...",

    # Injected item (from `as: panel_prompt`)
    "panel_prompt": "The knight approaches the castle...",

    # Map tracking
    "_map_index": 0,  # Index in the list
}
```

### Result Collection

Results include `_map_index` for ordering:

```python
animated_panels = [
    {"_map_index": 0, "first_frame": "...", "original": "...", "last_frame": "..."},
    {"_map_index": 1, "first_frame": "...", "original": "...", "last_frame": "..."},
    {"_map_index": 2, "first_frame": "...", "original": "...", "last_frame": "..."},
]
```

---

## Best Practices

1. **Keep sub-nodes simple**: One LLM call or one Python function per item
2. **Use descriptive `as` names**: `panel`, `document`, `item` - not `x` or `i`
3. **Handle empty lists**: Map nodes gracefully skip if the list is empty
4. **Order matters**: Results maintain order via `_map_index`
5. **State isolation**: Each sub-node gets a copy of state; mutations don't affect siblings

---

## Comparison with Other Patterns

| Pattern | Use Case | Parallelism |
|---------|----------|-------------|
| **Map** | Same operation on each item | Native parallel via `Send()` |
| **Loop** | Iterative refinement | Sequential |
| **Router** | Different paths based on classification | Single path |
| **Agent** | Autonomous tool selection | Sequential tool calls |

---

## Troubleshooting

### "List is empty"

```yaml
over: "{state.items}"  # Check that upstream node populates this
```

Ensure the `over` expression points to a populated list.

### "Cannot access field"

```yaml
as: panel
# In sub-node:
variables:
  prompt: "{state.panel}"        # ✅ Correct
  prompt: "{state.panel_prompt}" # ❌ Wrong if as: panel
```

The `as` name must match exactly in variables.

### Results not collected

The `collect` key is automatically added to state with a `sorted_add` reducer that:
- Collects results from all parallel branches
- Sorts by `_map_index` to maintain order

If results aren't appearing, check that:
1. The sub-node's `state_key` matches what you expect
2. The `collect` key name is spelled correctly
3. The sub-node is completing without errors
