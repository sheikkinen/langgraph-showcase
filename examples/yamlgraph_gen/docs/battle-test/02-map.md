# Test Case: Map Pattern

**Status:** ✅ PASSED (generator + framework fixed)

## Request

```
Take a list of topics and generate a short summary for each topic
```

## Reference

Compare with `graphs/map-demo.yaml`

## Validation Commands

```bash
cd examples/yamlgraph_gen

# Generate
python run_generator.py -o outputs/map-test \
  'Take a list of topics and generate a short summary for each topic'

# Structural checks
grep -A15 "type: map" outputs/map-test/graph.yaml
grep "items_key:" outputs/map-test/graph.yaml
grep "item_key:" outputs/map-test/graph.yaml
grep "state_key:" outputs/map-test/graph.yaml

# Execute
source ../../.env && cd outputs/map-test && \
yamlgraph graph run graph.yaml --var 'topics=["quantum computing", "machine learning", "blockchain"]'
```

## Success Criteria

- [x] Map node has type: map with over, as, node, collect fields
- [x] Sub-node defined under node: key
- [x] Prompt handles single item (not list)
- [x] Execution processes all items and aggregates results

## Results

### Generated Structure

```yaml
nodes:
  process_items:
    type: map
    over: "{state.topics}"
    as: topic
    node:
      prompt: generate_summary
      state_key: summary
      variables:
        topic: "{state.topic}"
    collect: summaries

  aggregate:
    type: llm
    prompt: aggregate_summaries
    state_key: final_summaries
    variables:
      summaries: "{state.summaries}"

edges:
  - from: START
    to: process_items
  - from: process_items
    to: aggregate
  - from: aggregate
    to: END
```

### Execution Output

```
Summaries collected: 3 items

Final aggregated output:
## Technology Summaries Overview
[Successfully generated formatted summaries for quantum computing, machine learning, and blockchain]
```

### Fixes Applied

| Component | Issue | Fix |
|-----------|-------|-----|
| snippets/nodes/map-basic.yaml | Used old API (input_key, sub_node) | Updated to current API (over, as, node, collect) |
| snippets/patterns/map-then-summarize.yaml | Map node had prompt field | Removed prompt, moved to nested sub-node |
| tools/snippet_loader.py | Couldn't find patterns in state.classification | Check both state.patterns and state.classification.patterns |
| yamlgraph/graph_loader.py | START -> map_node not supported | Added set_conditional_entry_point for map nodes |
