# Innovation Matrix Porting Plan

Migration from `innovation-matrix` Python project to YAMLGraph declarative graphs.

## Source Project Analysis

**Original**: `/src/innovation-matrix` (~20k lines Python)

| Component | Lines | YAMLGraph Equivalent |
|-----------|-------|---------------------|
| Matrix generation | ~500 | `graph.yaml` (25 lines) |
| Cell selection | ~200 | `select_cells.yaml` prompt |
| Cell expansion | ~300 | `drill-down.yaml` (31 lines) |
| RPG world pipeline | ~8000 | Out of scope |
| Story generation | ~6000 | Out of scope |
| Wiki export | ~2000 | Out of scope |

**Focus**: Core Innovation Matrix method only (not RPG/story use cases).

## Migration Phases

### Phase 1: Core Matrix Generation ✅

**Status**: Complete

**Files created**:
- `graph.yaml` - Single-node matrix generation
- `prompts/generate_matrix.yaml` - 5×5 matrix prompt

**Usage**:
```bash
yamlgraph graph run graph.yaml --var domain="AI in healthcare"
```

### Phase 2: Cell Drill-Down ✅

**Status**: Complete

**Files created**:
- `drill-down.yaml` - Cell expansion graph
- `prompts/expand_cell.yaml` - Deep exploration prompt

**Usage**:
```bash
yamlgraph graph run drill-down.yaml \
  --var domain="AI in healthcare" \
  --var capability="Diagnostic imaging" \
  --var constraint="Patient privacy"
```

### Phase 3: Full Pipeline with Map ⏳

**Status**: Not started

**Key Insight**: The "human block" between matrix generation and cell expansion was a
**porting artifact**, not a design choice. YAMLGraph makes map parallelism trivial.

**Architecture**:
```
domain → generate_matrix (structured output)
           ↓
       25 cells
           ↓
  ┌─────────────────────────────────────┐
  │    MAP over cells (parallel)        │
  │                                     │
  │    cell → web_search(cell.idea)     │  ← ground in reality
  │           ↓                         │
  │         expand_cell(cell + context) │  ← enriched expansion
  │                                     │
  └─────────────────────────────────────┘
           ↓
       25 expansions
           ↓
       synthesize_top_ideas (rank & filter)
           ↓
       Top 5 actionable ideas with evidence
```

**Cost Analysis** (~$0.80 total):
| Step | Calls | Est. Cost |
|------|-------|-----------|
| Generate matrix | 1 | ~$0.03 |
| Web search | 25 | ~$0 (free tier) |
| Expand cells | 25 | ~$0.75 |
| Synthesize | 1 | ~$0.03 |

**TODO**:
- [ ] Add inline schema to `generate_matrix.yaml` for structured cell output
- [ ] Create `pipeline.yaml` with map node over all 25 cells
- [ ] Add `prompts/synthesize_top_ideas.yaml` for final ranking
- [ ] Integrate web search tool (Tavily) for grounding

**Files to create**:
```yaml
# pipeline.yaml
nodes:
  generate:
    type: llm
    prompt: generate_matrix_structured
    state_key: matrix

  expand_all:
    type: map
    over: "{state.matrix.cells}"
    as: cell
    collect: expansions
    node:
      type: llm
      prompt: expand_cell
      variables:
        domain: "{state.domain}"
        capability: "{cell.capability}"
        constraint: "{cell.constraint}"
        cell_idea: "{cell.idea}"

  synthesize:
    type: llm
    prompt: synthesize_top_ideas
    state_key: top_ideas
```

### Phase 4: Web-Augmented Expansion ⏳

**Status**: Not started

**Concept**: Ground each cell expansion in real-world examples via web search.

**TODO**:
- [ ] Create `search-expand.yaml` subgraph (search → expand)
- [ ] Use web_search tool before expansion
- [ ] Pass search results as context to expand_cell prompt

### Phase 5: Recursive Matrix ⏳

**Status**: Not started

**Concept**: Second-order effects from cell expansion become inputs to new matrix.

**TODO**:
- [ ] Structured output from `expand_cell` with `new_capabilities` and `new_constraints`
- [ ] Loop graph that feeds outputs back as inputs
- [ ] Depth limit to prevent infinite recursion

### Phase 6: Optional Human Curation ⏳

**Status**: Not started

**Concept**: For budget-constrained or iterative refinement scenarios.

**TODO**:
- [ ] Create `interactive.yaml` with interrupt after matrix display
- [ ] User selects subset of cells (default: all)
- [ ] Add checkpointer for resuming partial explorations

## Key Differences from Original

| Original | YAMLGraph Port |
|----------|----------------|
| Python CLI commands | `yamlgraph graph run` |
| SQLite persistence | Checkpointer (sqlite/redis) |
| Custom models | Pydantic via `output_model` |
| Hardcoded pipelines | Declarative YAML graphs |
| RPG-specific | Domain-agnostic |

## Files Copied from Original

| Original | Destination | Notes |
|----------|-------------|-------|
| `graph/innovation-matrix.md` | `methodology.md` | Core method documentation |

## Files NOT Ported (Out of Scope)

- All RPG world generation prompts (`rpg-*`)
- Story pipeline (`story-*`)
- Wiki export
- Narrator integration
- Entity narrative bundles
- Prose generation

These are domain-specific applications built on top of the Innovation Matrix method, not the core method itself.

## Success Criteria

- [x] Can generate matrix for any domain (`graph.yaml`)
- [x] Can drill into any cell (`drill-down.yaml`)
- [ ] Can expand all 25 cells in parallel (`pipeline.yaml`)
- [ ] Can augment with web search for grounding
- [ ] Can synthesize top ideas from all expansions
- [ ] Full exploration for ~$0.80 vs manual curation
- [ ] ~150 lines YAML vs ~1000 lines Python for equivalent capability
