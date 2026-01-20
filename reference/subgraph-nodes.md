# Subgraph Nodes

Subgraph nodes enable modular graph composition by embedding one graph inside another. This allows reusable workflows to be packaged and invoked as single nodes.

## Quick Start

```yaml
# graphs/parent.yaml
nodes:
  summarize:
    type: subgraph
    graph: subgraphs/summarizer.yaml
    input_mapping:
      my_text: input_text        # parent state → child state
    output_mapping:
      summary: output_summary    # child state → parent state
```

```yaml
# graphs/subgraphs/summarizer.yaml
state:
  input_text: str
  output_summary: str

nodes:
  summarize:
    type: llm
    prompt: summarizer/summarize
    state_key: output_summary
```

## Configuration

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `type` | `"subgraph"` | ✅ | Node type identifier |
| `graph` | `string` | ✅ | Path to child graph YAML (relative to workspace) |
| `mode` | `string` | - | Execution mode: `invoke` (default) or `stream` |
| `input_mapping` | `dict` | - | Map parent state keys → child state keys |
| `output_mapping` | `dict` | - | Map child state keys → parent state keys |

## State Mapping

### Input Mapping

Pass data from parent graph to child graph:

```yaml
nodes:
  analyze:
    type: subgraph
    graph: subgraphs/analyzer.yaml
    input_mapping:
      document: input_doc      # parent.document → child.input_doc
      context: analysis_ctx    # parent.context → child.analysis_ctx
```

The child graph receives `input_doc` and `analysis_ctx` in its initial state.

### Output Mapping

Receive results from child graph:

```yaml
nodes:
  analyze:
    type: subgraph
    graph: subgraphs/analyzer.yaml
    output_mapping:
      result: analysis_output  # child.analysis_output → parent.result
      score: confidence        # child.confidence → parent.score
```

After the child graph completes, `result` and `score` are updated in parent state.

## Execution Modes

### Invoke Mode (Default)

Run child graph synchronously, wait for completion:

```yaml
nodes:
  summarize:
    type: subgraph
    mode: invoke
    graph: subgraphs/summarizer.yaml
```

### Stream Mode

Stream child graph execution for long-running subgraphs:

```yaml
nodes:
  research:
    type: subgraph
    mode: stream
    graph: subgraphs/researcher.yaml
```

## Complete Example

### Parent Graph

```yaml
# graphs/document-processor.yaml
version: "1.0"
name: document-processor

state:
  raw_text: str
  prepared_text: str
  summary: str
  final_output: str

nodes:
  prepare:
    type: llm
    prompt: processor/prepare
    state_key: prepared_text

  summarize:
    type: subgraph
    mode: invoke
    graph: subgraphs/summarizer.yaml
    input_mapping:
      prepared_text: input_text
    output_mapping:
      summary: output_summary

  format:
    type: llm
    prompt: processor/format
    state_key: final_output

edges:
  - from: START
    to: prepare
  - from: prepare
    to: summarize
  - from: summarize
    to: format
  - from: format
    to: END
```

### Child Graph

```yaml
# graphs/subgraphs/summarizer.yaml
version: "1.0"
name: summarizer
description: Reusable text summarization subgraph

state:
  input_text: str
  output_summary: str

nodes:
  summarize:
    type: llm
    prompt: summarizer/summarize
    state_key: output_summary

edges:
  - from: START
    to: summarize
  - from: summarize
    to: END
```

## Use Cases

| Pattern | Description |
|---------|-------------|
| **Reusable workflows** | Package common patterns (summarization, validation) |
| **Domain separation** | Keep domain logic in separate files |
| **Testing** | Test subgraphs independently |
| **Team collaboration** | Different teams own different subgraphs |

## Nesting

Subgraphs can contain other subgraphs for hierarchical composition:

```
parent.yaml
  └── analyzer.yaml (subgraph)
        └── validator.yaml (nested subgraph)
```

Each level has its own state, mapped through `input_mapping` and `output_mapping`.

## Best Practices

1. **Clear interfaces** - Document expected input/output state keys
2. **Self-contained** - Subgraphs should work independently
3. **Organize in folder** - Use `graphs/subgraphs/` for reusable graphs
4. **Consistent naming** - Use `input_*` and `output_*` for interface keys
