# FR-033: Sequence Syntax for Linear Flows

**Status**: Proposed
**Priority**: P1
**Effort**: 1-2 days
**Created**: 2026-02-13

## Summary

Add `sequence:` syntax to define linear node chains without explicit edge definitions, using LangGraph's `add_sequence()`.

## Problem

Sequential nodes require verbose edge definitions:

```yaml
# Current: 8 lines for 3-node chain
edges:
  - from: START
    to: step1
  - from: step1
    to: step2
  - from: step2
    to: step3
  - from: step3
    to: END
```

This is:
- **Verbose**: N nodes = 2N lines of edges
- **Error-prone**: Easy to miswire or forget an edge
- **Noisy**: Intent (linear flow) obscured by mechanics (edge definitions)

## Solution

LangGraph's `add_sequence()` chains nodes automatically:

```python
graph.add_sequence([step1, step2, step3])
# Creates: START → step1 → step2 → step3 → END
```

## Proposed YAML Syntax

```yaml
# Option A: Replace edges entirely for linear flows
sequence:
  - step1
  - step2
  - step3

# 4 lines vs 8 lines = 50% reduction
```

```yaml
# Option B: Mixed mode (sequence + branching)
sequence:
  - parse
  - analyze
  - decide  # Last node can branch

edges:
  - from: decide
    to: [approve, reject]
    type: conditional
```

```yaml
# Option C: Multiple sequences (parallel linear chains)
sequences:
  main:
    - input
    - process
    - output
  fallback:
    - detect_error
    - handle_error
    - recover
```

## Use Cases

### UC1: ETL Pipeline

**Scenario**: Extract → Transform → Load pattern.

**Current**:
```yaml
edges:
  - from: START
    to: extract
  - from: extract
    to: transform
  - from: transform
    to: load
  - from: load
    to: END
```

**Proposed**:
```yaml
sequence:
  - extract
  - transform
  - load
```

**Savings**: 4 lines (50% reduction)

### UC2: Document Processing

**Scenario**: Parse → Chunk → Embed → Store.

**Current**:
```yaml
edges:
  - from: START
    to: parse_document
  - from: parse_document
    to: chunk_text
  - from: chunk_text
    to: generate_embeddings
  - from: generate_embeddings
    to: store_vectors
  - from: store_vectors
    to: END
```

**Proposed**:
```yaml
sequence:
  - parse_document
  - chunk_text
  - generate_embeddings
  - store_vectors
```

**Savings**: 6 lines (55% reduction)

### UC3: Multi-Stage Analysis

**Scenario**: Research → Draft → Review → Revise → Publish.

**Current**:
```yaml
edges:
  - from: START
    to: research
  - from: research
    to: draft
  - from: draft
    to: review
  - from: review
    to: revise
  - from: revise
    to: publish
  - from: publish
    to: END
```

**Proposed**:
```yaml
sequence:
  - research
  - draft
  - review
  - revise
  - publish
```

**Savings**: 9 lines (64% reduction)

### UC4: Innovation Matrix Pipeline

**Scenario**: generate_dimensions → cartesian → expand_all → synthesize.

**Current** (from `innovation_matrix/pipeline.yaml`):
```yaml
edges:
  - from: START
    to: generate_dimensions
  - from: generate_dimensions
    to: cartesian
  - from: cartesian
    to: expand_all
  - from: expand_all
    to: synthesize
  - from: synthesize
    to: END
```

**Proposed**:
```yaml
sequence:
  - generate_dimensions
  - cartesian
  - expand_all
  - synthesize
```

**Savings**: 6 lines (55% reduction)

## Business Value

| Metric | Current | With Sequence |
|--------|---------|---------------|
| Lines per linear graph | N×2 | N |
| YAML complexity | High | Low |
| Wiring errors | Common | Impossible |
| Graph intent | Hidden | Obvious |

## Implementation

1. **Schema** (0.5 day): Add `sequence` field to GraphConfig
2. **Loader** (0.5 day): Convert sequence to edges before compilation
3. **Mixed mode** (0.5 day): Handle sequence + edges coexistence
4. **Validation** (0.25 day): Error if sequence nodes not defined
5. **Tests** (0.25 day): All syntax variations

## Conversion Logic

```python
def convert_sequence_to_edges(sequence: list[str]) -> list[Edge]:
    edges = [Edge(from_node="START", to_node=sequence[0])]
    for i in range(len(sequence) - 1):
        edges.append(Edge(from_node=sequence[i], to_node=sequence[i + 1]))
    edges.append(Edge(from_node=sequence[-1], to_node="END"))
    return edges
```

## Backward Compatibility

- 100% compatible - `edges:` still works
- `sequence:` is purely additive
- Linter warns if both `sequence:` and conflicting `edges:` defined

## Validation Rules

1. All nodes in sequence must be defined in `nodes:`
2. If `sequence:` present, `edges:` cannot define START→first or last→END
3. Sequence cannot contain conditional nodes (use `edges:` for those)

## Dependencies

- None (leverages existing edge handling)
- LangGraph `add_sequence()` for future optimization
