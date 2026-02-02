# Data Files Demo - External Configuration

This demo shows how to use the `data_files` directive to load external
YAML configuration into graph state at compile time.

## Use Case

A survey system where field definitions are stored separately from the
graph logic, enabling:
- Schema reuse across multiple graphs
- Non-developer editing of field definitions
- Version control of schemas independent of graph logic

## Run

```bash
yamlgraph run examples/demos/data-files/graph.yaml --var "response=I rate it 8/10, great product but shipping was slow"
```

## Files

- `graph.yaml` - Main graph definition with `data_files`
- `schema.yaml` - Field definitions loaded at compile time
- `prompts/extract.yaml` - Extraction prompt using schema fields
