# Subgraph Demo

Graph composition using `type: subgraph`.

## Usage

```bash
yamlgraph graph run examples/demos/subgraph/graph.yaml \
  --var raw_text="LangGraph is a library for building stateful applications..."
```

## What It Does

1. **Parent graph** preprocesses text
2. **Child subgraph** summarizes (reusable component)
3. **Parent graph** formats final output

## Pipeline

```
Parent:  START → prepare → [summarizer subgraph] → format → END
                                    │
Child:           START → summarize → analyze → END
```

## Key Concepts

- **`type: subgraph`** - Embed another graph as a node
- **State mapping** - Map parent state to child inputs
- **Composition** - Reuse graphs as components

## Subgraph Node Configuration

```yaml
nodes:
  summarize:
    type: subgraph
    graph: subgraphs/summarizer.yaml
    input_mapping:
      text: "{state.prepared_text}"
    output_mapping:
      summary: summary
```

## State Mapping

| Direction | Property | Description |
|-----------|----------|-------------|
| In | `input_mapping` | Parent state → Child inputs |
| Out | `output_mapping` | Child outputs → Parent state |

## Files

```
subgraph/
├── graph.yaml              # Parent graph
├── prompts/
│   └── prepare.yaml
└── subgraphs/
    └── summarizer.yaml     # Child graph
```

## Learning Path

Advanced pattern after mastering basic nodes. Enables modular graph design.
