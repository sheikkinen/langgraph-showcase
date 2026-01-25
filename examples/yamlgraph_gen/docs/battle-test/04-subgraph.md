# Test Case: Subgraph Pattern

**Status:** ❌ Not supported

## Request

```
Create a modular pipeline where document processing is a reusable subgraph
```

## Why Not Supported

The generator only creates a single `graph.yaml`. Subgraph pattern requires:

1. Main graph with `type: subgraph` node
2. Separate subgraph YAML file
3. State mapping between graphs

## What Would Be Needed

### Generator Changes

1. Detect subgraph pattern in classification
2. Generate multiple files:
   - `graph.yaml` (main graph)
   - `subgraphs/document_processor.yaml` (subgraph)
3. Add state mapping in main graph node

### Expected Output Structure

```
outputs/subgraph-test/
├── graph.yaml
├── prompts/
│   └── ...
└── subgraphs/
    └── document_processor.yaml
```

### Expected Main Graph Node

```yaml
nodes:
  process_document:
    type: subgraph
    graph: subgraphs/document_processor.yaml
    input_mapping:
      document: "{state.current_document}"
    output_mapping:
      processed: processed_result
```

## Recommendation

Skip until generator supports multi-file output.

## Results

_N/A - test deferred_
