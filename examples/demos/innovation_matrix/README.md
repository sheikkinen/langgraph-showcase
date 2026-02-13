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
# Generate a matrix (markdown output)
yamlgraph graph run examples/demos/innovation_matrix/graph.yaml \
  --var domain="sustainable packaging"

# Drill into a specific cell
yamlgraph graph run examples/demos/innovation_matrix/drill-down.yaml \
  --var domain="sustainable packaging" \
  --var capability="Biodegradable materials" \
  --var constraint="Cost parity"

# Full pipeline: expand all 25 cells (~$0.80, ~70s)
PROVIDER=anthropic yamlgraph graph run examples/demos/innovation_matrix/pipeline.yaml \
  --var domain="sustainable packaging" --full
```

> **Note**: The pipeline uses parallel LLM calls. Use a cloud provider (Anthropic/OpenAI) for best results.
> Local LLMs (LM Studio) will hang on 25 parallel requests.

## Files

| File | Purpose |
|------|---------|
| `graph.yaml` | Generate 5×5 matrix (markdown) |
| `drill-down.yaml` | Expand a specific cell |
| `pipeline.yaml` | Full pipeline: dimensions → 25 expansions → top 5 |
| `prompts/generate_matrix.yaml` | Matrix generation (markdown) |
| `prompts/generate_dimensions.yaml` | Extract capabilities + constraints (structured) |
| `prompts/expand_cell.yaml` | Cell deep expansion |
| `prompts/synthesize.yaml` | Rank top 5 ideas |
| `nodes/cartesian.py` | Generate 25 cap×con pairs |

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| **1. Matrix Generation** | ✅ | `graph.yaml` - markdown output |
| **2. Cell Drill-Down** | ✅ | `drill-down.yaml` - single cell expansion |
| **3. Full Pipeline** | ✅ | `pipeline.yaml` - all 25 cells in parallel |
| **4. Web-Augmented** | ⏳ | Ground expansions with web search |
| **5. Recursive** | ⏳ | Second-order effects → new dimensions |
| **6. Interactive** | ⏳ | Human cell selection via interrupt |

## Usage Patterns

### Pattern 1: Quick Ideation
Generate matrix, manually pick cells to explore:
```bash
yamlgraph graph run examples/demos/innovation_matrix/graph.yaml \
  --var domain="sustainable packaging"
# Read output, pick interesting cell
yamlgraph graph run examples/demos/innovation_matrix/drill-down.yaml \
  --var domain="sustainable packaging" \
  --var capability="Biodegradable materials" \
  --var constraint="Cost parity"
```

### Pattern 2: Full Exploration
Expand all 25 cells and synthesize top ideas:
```bash
PROVIDER=anthropic yamlgraph graph run examples/demos/innovation_matrix/pipeline.yaml \
  --var domain="sustainable packaging" --full
```

### Pattern 3: Recursive Deepening
Output of one matrix becomes input to next:
```bash
# Level 0: Abstract domain
yamlgraph graph run examples/demos/innovation_matrix/graph.yaml \
  --var domain="future of cities"
# Level 1: Specific intersection from results
yamlgraph graph run examples/demos/innovation_matrix/graph.yaml \
  --var domain="smart infrastructure × aging population"
```

## Key Insight

> The best ideas don't come from **adding features**.
> They come from **colliding possibilities with limits**.

The Innovation Matrix systematizes this collision.

## Origin

Adapted from the [innovation-matrix](https://github.com/sheikkinen/innovation-matrix) project,
focusing on the core matrix methodology without domain-specific pipelines.
