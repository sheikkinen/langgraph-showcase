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

### Phase 3: AI Cell Selection ⏳

**Status**: Prompt ready, graph not integrated

**Files**:
- `prompts/select_cells.yaml` ✅

**TODO**:
- [ ] Create `select.yaml` graph
- [ ] Create `full-pipeline.yaml` that chains: generate → select → expand

### Phase 4: Interactive Selection ⏳

**Status**: Not started

**Approach**: Use YAMLGraph interrupt nodes for human-in-the-loop cell selection.

**TODO**:
- [ ] Create `interactive.yaml` with interrupt after matrix display
- [ ] User selects cells manually
- [ ] Continue to expansion

### Phase 5: Recursive Matrix ⏳

**Status**: Not started

**Concept**: Second-order effects from cell expansion become inputs to new matrix.

**TODO**:
- [ ] Structured output from `expand_cell` with `new_capabilities` and `new_constraints`
- [ ] Loop graph that feeds outputs back as inputs
- [ ] Depth limit to prevent infinite recursion

### Phase 6: Memory/Persistence ⏳

**Status**: Not started

**Concept**: Store matrix exploration history for iterative refinement.

**TODO**:
- [ ] Add checkpointer configuration
- [ ] Resume partial explorations
- [ ] Export exploration tree

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

- [ ] Can generate matrix for any domain
- [ ] Can drill into any cell
- [ ] Can chain multiple exploration levels
- [ ] ~100 lines YAML vs ~1000 lines Python for equivalent capability
