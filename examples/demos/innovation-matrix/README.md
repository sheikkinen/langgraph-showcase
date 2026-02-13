# Innovation Matrix Demo

A YAMLGraph implementation of the **Innovation Matrix** creativity method.

## The Method

The Innovation Matrix generates ideas by crossing **Capabilities** (what's possible) with **Constraints** (what limits) to create creative tensions.

```
                 CONSTRAINTS
              ┌─────┬─────┬─────┬─────┬─────┐
              │ S1  │ S2  │ S3  │ S4  │ S5  │
         ┌────┼─────┼─────┼─────┼─────┼─────┤
    C    │ C1 │ C1S1│ C1S2│ C1S3│ C1S4│ C1S5│
    A    ├────┼─────┼─────┼─────┼─────┼─────┤
    P    │ C2 │ C2S1│ C2S2│ C2S3│ C2S4│ C2S5│
    A    ├────┼─────┼─────┼─────┼─────┼─────┤
    B    │ C3 │ C3S1│ C3S2│ C3S3│ C3S4│ C3S5│
    I    ├────┼─────┼─────┼─────┼─────┼─────┤
    L    │ C4 │ C4S1│ C4S2│ C4S3│ C4S4│ C4S5│
    I    ├────┼─────┼─────┼─────┼─────┼─────┤
    T    │ C5 │ C5S1│ C5S2│ C5S3│ C5S4│ C5S5│
    Y    └────┴─────┴─────┴─────┴─────┴─────┘

Each cell = a creative intersection to explore
```

## Quick Start

```bash
# Generate a matrix for a domain
yamlgraph graph run examples/demos/innovation-matrix/graph.yaml \
  --var domain="AI-powered education"

# Drill into a specific cell
yamlgraph graph run examples/demos/innovation-matrix/drill-down.yaml \
  --var domain="AI-powered education" \
  --var capability="Personalized learning paths" \
  --var constraint="Student attention spans"
```

## Files

| File | Purpose |
|------|---------|
| `graph.yaml` | Generate 5×5 matrix from domain |
| `drill-down.yaml` | Expand a specific cell |
| `prompts/generate_matrix.yaml` | Matrix generation prompt |
| `prompts/select_cells.yaml` | Cell selection prompt |
| `prompts/expand_cell.yaml` | Cell expansion prompt |

## Porting Plan

### Phase 1: Core Matrix Generation ✅
- [x] `generate_matrix` prompt - Create 5×5 matrix from domain
- [x] `graph.yaml` - Single-node matrix generation

### Phase 2: Cell Selection
- [x] `select_cells` prompt - AI picks top N cells
- [ ] Add selection node to graph

### Phase 3: Recursive Drill-Down ✅
- [x] `expand_cell` prompt - Deep dive into intersection
- [x] `drill-down.yaml` - Cell expansion graph

### Phase 4: Full Pipeline (Future)
- [ ] Multi-node graph: generate → select → expand (map over selected)
- [ ] Interrupt node for manual cell selection
- [ ] Memory/checkpointer for iterative refinement
- [ ] Second-order effects feeding back as new dimensions

### Phase 5: Advanced Features (Future)
- [ ] Custom dimensions via `data_files`
- [ ] Matrix visualization output
- [ ] Export to structured JSON for further processing

## Usage Patterns

### Pattern 1: Quick Ideation
Generate matrix, manually pick cells to explore:
```bash
yamlgraph graph run graph.yaml --var domain="sustainable packaging"
# Read output, pick interesting cell
yamlgraph graph run drill-down.yaml \
  --var domain="sustainable packaging" \
  --var capability="Biodegradable materials" \
  --var constraint="Cost parity with plastic"
```

### Pattern 2: AI-Assisted Exploration
Let AI select promising cells:
```bash
yamlgraph graph run full-pipeline.yaml --var domain="remote work tools"
```

### Pattern 3: Recursive Deepening
Output of one matrix becomes input to next:
```bash
# Level 0: Abstract domain
yamlgraph graph run graph.yaml --var domain="future of cities"
# Level 1: Specific intersection
yamlgraph graph run graph.yaml --var domain="smart infrastructure × aging population"
# Level 2: Even more specific
yamlgraph graph run graph.yaml --var domain="accessible transit × sensor networks × budget cuts"
```

## Key Insight

> The best ideas don't come from **adding features**.
> They come from **colliding possibilities with limits**.

The Innovation Matrix systematizes this collision.

## Origin

Adapted from the [innovation-matrix](https://github.com/sheikkinen/innovation-matrix) project,
focusing on the core matrix methodology without domain-specific pipelines.
