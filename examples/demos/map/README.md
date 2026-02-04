# Map Demo

Parallel fan-out processing using `type: map`.

## Usage

```bash
yamlgraph graph run examples/demos/map/graph.yaml --var topic="Space"
```

## What It Does

1. **Generate** - Creates a list of ideas about the topic
2. **Expand (parallel)** - Each idea is expanded in parallel using map
3. **Summarize** - Combines all expanded ideas

## Pipeline

```
                    ┌→ expand[0] ─┐
START → generate ──→├→ expand[1] ─├→ summarize → END
                    └→ expand[2] ─┘
```

## Key Concepts

- **`type: map`** - Parallel fan-out node
- **`source`** - State key containing list to iterate
- **`node`** - Sub-node configuration applied to each item
- **`state_key`** - Collects results back into list

## Map Node Configuration

```yaml
expand:
  type: map
  source: "{state.ideas}"      # List to iterate over
  node:
    type: llm
    prompt: expand_idea
    variables:
      idea: "{item}"           # Current item in iteration
  state_key: expanded_ideas    # Results collected here
```

## How It Works

1. Map node receives list from `source`
2. Creates parallel `Send()` for each item
3. Sub-node processes each item independently
4. Results collected in `state_key` (sorted by index)

## Learning Path

After [router](../router/). Next: [reflexion](../reflexion/) for self-correction loops.
