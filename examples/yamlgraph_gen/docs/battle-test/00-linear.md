# Test Case: Linear Pattern

**Status:** ✅ Tested

## Request

```
Create a simple summarizer that takes text and produces a summary
```

## Reference

Most basic pattern - sequential nodes.

## Validation Commands

```bash
cd examples/yamlgraph_gen

# Generate
python run_generator.py -o outputs/linear-test \
  'Create a simple summarizer that takes text and produces a summary'

# Structural checks
grep "type: llm" outputs/linear-test/graph.yaml
grep -A10 "edges:" outputs/linear-test/graph.yaml

# Execute
source ../../.env && cd outputs/linear-test && \
yamlgraph graph run graph.yaml --var 'text=The quick brown fox jumps over the lazy dog. This is a test sentence for summarization.'
```

## Success Criteria

- [x] LLM nodes have type: llm
- [x] Edges form linear sequence (START → node1 → node2 → END)
- [x] State fields defined for input/output
- [x] Prompts exist for all nodes
- [x] Execution produces summary output

## Results

### Generated Structure

Tested successfully. Basic linear graph generates correctly.

### Issues Found

None - linear pattern is the default and works reliably.
