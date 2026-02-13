# Innovation Matrix - YAMLGraph Port

Core Innovation Matrix method ported from `innovation-matrix` Python project (~20k LOC → ~150 LOC YAML).

## Current State

| File | Status | Purpose |
|------|--------|---------|
| `graph.yaml` | ✅ | Generate 5×5 matrix (markdown) |
| `drill-down.yaml` | ✅ | Expand single cell |

## Constraint

**YAMLGraph inline schemas do NOT support nested objects.**

`schema_loader.py` only supports: `str`, `int`, `float`, `bool`, `list[T]`, `dict[K,V]` where T/K/V are basic types.

`list[{id: str, ...}]` **will not compile**.

## Solution: Two-Step Generation

Decompose matrix generation into simple-typed steps:

```
domain → generate_dimensions → {capabilities: list[str], constraints: list[str]}
                   ↓
         cartesian_product (tool) → 25 {cap, con} pairs
                   ↓
              MAP(expand_cell) → 25 expansions
                   ↓
           synthesize → top 5
```

## Phase 3 (Revised)

| Step | File | Output Type |
|------|------|-------------|
| **3a** | `prompts/generate_dimensions.yaml` | `{capabilities: list[str], constraints: list[str]}` |
| **3b** | `nodes/cartesian.py` | Tool: `list[{cap, con}]` from state |
| **3c** | `pipeline.yaml` | Map over 25 pairs |
| **3d** | `prompts/synthesize.yaml` | Top 5 ranking |

**Cost**: ~$0.80 for complete domain exploration.

## Future Phases (out of scope)

| Phase | Concept |
|-------|---------|
| **4. Web-Augmented** | Ground expansions in real examples via search |
| **5. Recursive** | Second-order effects → new matrix dimensions |
| **6. Interactive** | Interrupt node for human cell selection |

## Acceptance Criteria

- [x] Generate matrix for any domain (markdown)
- [x] Drill into any cell
- [x] **3a**: Generate dimensions as simple lists
- [x] **3b**: Cartesian product tool
- [x] **3c**: Pipeline maps over all 25 pairs
- [x] **3d**: Synthesize to top 5

## Demo Commands

```bash
# Phase 1: Quick matrix (markdown output)
yamlgraph graph run examples/demos/innovation_matrix/graph.yaml \
  --var domain="sustainable packaging"

# Phase 2: Drill into one cell
yamlgraph graph run examples/demos/innovation_matrix/drill-down.yaml \
  --var domain="sustainable packaging" \
  --var capability="Biodegradable materials" \
  --var constraint="Cost parity"

# Phase 3: Full pipeline (~$0.80, 25 LLM calls)
yamlgraph graph run examples/demos/innovation_matrix/pipeline.yaml \
  --var domain="sustainable packaging"
```
