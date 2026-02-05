# Python Map Demo

Demonstrates `type: python` sub-nodes in map nodes (FR-021).

## What This Shows

- Fan-out over a list with **Python tools** instead of LLM calls
- Parallel processing with `_map_index` preservation
- Pure Python demo - no API keys needed

## Usage

```bash
yamlgraph graph run examples/demos/python-map/graph.yaml \
  --var 'texts=["Hello world!", "How are you today?", "This is a longer sentence."]' \
  --full
```

## Expected Output

```yaml
analyses:
  - _map_index: 0
    char_count: 12
    word_count: 2
    avg_word_len: 5.0
    has_question: false
  - _map_index: 1
    char_count: 18
    word_count: 4
    avg_word_len: 3.5
    has_question: true
  - _map_index: 2
    char_count: 26
    word_count: 5
    avg_word_len: 4.2
    has_question: false
```

## Key Pattern

```yaml
nodes:
  analyze:
    type: map
    over: "{state.texts}"
    as: text
    collect: analyses
    node:
      type: python        # <-- Python instead of LLM
      tool: analyze_text
      state_key: stats
```
