# YAMLGraph Pipeline Demo

Content generation pipeline: generate → analyze → summarize.

## Usage

```bash
yamlgraph graph run examples/demos/yamlgraph/graph.yaml \
  --var topic="AI" --var style="casual"
```

## What It Does

1. **Generate** - Create content about the topic
2. **Analyze** - Extract key insights
3. **Summarize** - Create final summary

## Pipeline

```
START → generate → analyze → summarize → END
```

## Key Concepts

- **Linear pipeline** - Sequential node execution
- **State flow** - Each node reads previous output
- **Dependency chain** - `requires` ensures ordering

## Node Dependencies

```yaml
nodes:
  analyze:
    requires: [generated]  # Wait for generate node
    variables:
      content: "{state.generated}"
```

## Learning Path

This demonstrates a basic multi-step pipeline. Similar to [hello](../hello/) but with more steps.
