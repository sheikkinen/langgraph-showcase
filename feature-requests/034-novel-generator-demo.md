# FR-034: Novel Generator Demo

**Status:** Complete
**Priority:** P2 (Marketing Showcase)
**Effort:** 15 hours
**Type:** Example (no core extensions required)

## Summary

Port a streamlined novel generation demo from the original `innovation-matrix/narrator` project. **Marketing showcase** demonstrating YAMLGraph's evolution loops, map nodes, and quality gates in a creative writing context.

## Marketing Rationale

**Success Story Narrative:**
> "We ported a 4000-line Python novel generator to YAMLGraph.
> The result: 7 YAML files, 80-line graph, and a junior developer
> can understand the entire pipeline."

**Why This Demo:**
- Creative domain (universally understood)
- Multi-phase architecture (real complexity)
- Tangible output (readable story)
- Compelling comparison: 4000 lines Python → ~100 lines YAML

**Current Demo Gap:**
| Demo | Limitation |
|------|------------|
| `hello/` | Too trivial |
| `reflexion/` | Single loop, narrow domain |
| `innovation_matrix/` | Abstract domain |
| `map/` | Pattern-focused, not application-focused |

Novel generator fills the "compelling success story" gap.

## Analysis: Example vs Core Extension

### Verdict: **Pure Example**

All required functionality exists in YAMLGraph core:

| Pattern | Required Feature | YAMLGraph Status |
|---------|------------------|------------------|
| Evolution loop | Conditional routing | ✅ Supported |
| Quality gates | Conditional edges with expression | ✅ Supported |
| Map-based prose | Map node type | ✅ REQ-YG-024/040/041 |
| Structured output | Inline YAML schemas | ✅ Supported |
| Review loop | Conditional routing | ✅ Supported |

**No new node types, no new routing logic, no core changes needed.**

## Scope

### What We're Building

A 3-phase creative writing pipeline using **existing** YAMLGraph features:

```
Phase 1: Ideation     - Synopsis evolution loop (generate → analyze → evolve)
Phase 2: Generation   - Map node for parallel prose per beat
Phase 3: Assembly     - Review gate with optional revision
```

### Files to Create

```
examples/demos/novel_generator/
├── graph.yaml                    # Main graph (existing patterns)
├── README.md                     # Demo documentation
├── prompts/
│   ├── synopsis/
│   │   ├── generate.yaml        # LLM node prompt
│   │   ├── analyze.yaml         # LLM node prompt
│   │   └── evolve.yaml          # LLM node prompt
│   ├── timeline/
│   │   └── construct.yaml       # LLM node prompt
│   ├── prose/
│   │   └── generate_beat.yaml   # Map node prompt
│   └── review/
│       ├── review.yaml          # LLM node prompt
│       └── revise.yaml          # LLM node prompt
└── schemas/
    ├── synopsis.py              # Pydantic models
    ├── timeline.py              # Pydantic models
    └── review.py                # Pydantic models
```

## Graph Design

### Phase 1: Synopsis Evolution (Evolution Loop Pattern)

Uses standard conditional edges:

```yaml
nodes:
  generate_synopsis:
    type: llm
    prompt: prompts/synopsis/generate.yaml
    state_key: synopsis

  analyze_synopsis:
    type: llm
    prompt: prompts/synopsis/analyze.yaml
    state_key: analysis

  evolve_synopsis:
    type: llm
    prompt: prompts/synopsis/evolve.yaml
    state_key: synopsis

edges:
  START: generate_synopsis
  generate_synopsis: analyze_synopsis
  analyze_synopsis:
    condition: "analysis.grade >= 'B'"
    true: construct_timeline
    false: evolve_synopsis
  evolve_synopsis: analyze_synopsis
```

### Phase 2: Parallel Prose Generation (Map Node Pattern)

Uses existing map node:

```yaml
nodes:
  construct_timeline:
    type: llm
    prompt: prompts/timeline/construct.yaml
    state_key: timeline

  generate_prose:
    type: map
    prompt: prompts/prose/generate_beat.yaml
    items_key: timeline.beats
    state_key: prose_sections

edges:
  construct_timeline: generate_prose
  generate_prose: review_draft
```

### Phase 3: Review Gate (Conditional Loop Pattern)

Uses standard conditional edges:

```yaml
nodes:
  review_draft:
    type: llm
    prompt: prompts/review/review.yaml
    state_key: review

  revise_draft:
    type: llm
    prompt: prompts/review/revise.yaml
    state_key: prose_sections

edges:
  review_draft:
    condition: "review.passed"
    true: END
    false: revise_draft
  revise_draft: review_draft
```

## CLI Usage

```bash
# Full story generation
yamlgraph graph run examples/demos/novel_generator/graph.yaml \
  --var premise="A lighthouse keeper discovers her parents' disappearance is connected to a ghost ship" \
  --var genre="dark fantasy" \
  --var target_beats=10

# Quick test (3 beats)
yamlgraph graph run examples/demos/novel_generator/graph.yaml \
  --var premise="A baker who can taste emotions" \
  --var target_beats=3
```

## Acceptance Criteria

**Readability (Key Success Metric):**
1. [ ] Any developer can understand graph.yaml in 5 minutes
2. [ ] graph.yaml is ≤100 lines (with comments)
3. [ ] 3 phases clearly labeled with comments

**Functionality:**
4. [ ] `yamlgraph graph lint` passes on graph.yaml
5. [ ] Evolution loop iterates 2-3 times before proceeding
6. [ ] Map node generates prose for 3+ beats in parallel
7. [ ] Review gate catches intentionally poor output
8. [ ] `--var target_beats=3` completes in <2 minutes

**Documentation:**
9. [ ] README tells "4000→100 lines" success story
10. [ ] Generated output is coherent (manual review)

## Readability Constraints

| Constraint | Reason |
|------------|--------|
| **Max 100 lines graph.yaml** | Readability for non-experts |
| **Max 7 prompts** | Complexity budget |
| **3 phases clearly labeled** | Narrative structure |
| **Comments in graph.yaml** | Self-documenting showcase |
| **README tells the story** | "4000 lines → 100 lines" narrative |
| **Working with `--var target_beats=3`** | Quick demo mode |

## What We're NOT Porting

| Feature | Reason |
|---------|--------|
| 9 parallel reviewers | Overkill; 1 reviewer sufficient |
| SQLite persistence | Use checkpointers |
| IssueTracker | Complex; not needed for demo |
| ReAct revision agent | Too complex |
| Entity narratives | Domain-specific |
| Editorial/Polish tools | Separate packages |
| Prose versioning | Complex |

## Comparison: Original vs Port

| Aspect | Original Narrator | YAMLGraph Port |
|--------|-------------------|----------------|
| Python code | ~4000 lines | ~100 lines (schemas) |
| Prompts | 30+ YAML | 7 YAML |
| Graph definition | Python StateGraph | Pure YAML |
| Reviewers | 9 parallel | 1 |
| Beats | 30-40 | 5-15 |

## Tasks

| Task | Hours | Notes |
|------|-------|-------|
| **Tests First** | | |
| Write failing tests | 1.5h | TDD red phase - uses existing REQs |
| **Implementation** | | |
| Graph design (with comments) | 3h | Key deliverable - must be clean |
| Synopsis prompts (3) | 2h | generate, analyze, evolve |
| Timeline prompt | 1h | |
| Prose generation prompt | 1.5h | |
| Review prompts (2) | 1.5h | review, revise |
| Pydantic schemas | 1h | |
| **Validation** | | |
| Run tests (green phase) | 1h | All tests pass |
| Refactor | 0.5h | Clean up |
| **Documentation** | | |
| **README (success story)** | 2h | Key marketing artifact |
| **Total** | **15h** | |

## TDD Artifacts (Marketing: Development Pipeline)

**Intent:** Showcase YAMLGraph's development rigor as part of the success story.

**Rationale:** The demo exercises *existing* requirements; it doesn't create new framework capabilities. Tests reference existing REQs that the demo validates in a creative writing context.

### Test File: `tests/integration/test_novel_generator.py`

```python
"""Integration tests for novel generator demo.

Exercises existing requirements in a creative writing context.
Marketing artifact: demonstrates TDD approach to example development.
"""
import pytest

@pytest.mark.req("REQ-YG-024")  # Conditional routing
def test_evolution_loop_improves_synopsis():
    """Synopsis quality improves over iterations."""
    pass

@pytest.mark.req("REQ-YG-040")  # Map node compilation
def test_map_node_generates_parallel_prose():
    """Map node generates prose for multiple beats."""
    pass

@pytest.mark.req("REQ-YG-024")  # Conditional routing
def test_review_gate_routes_correctly():
    """Review gate routes based on quality."""
    pass

@pytest.mark.req("REQ-YG-024", "REQ-YG-040")
def test_full_pipeline_end_to_end():
    """Full pipeline exercises multiple requirements."""
    pass
```

### RTM Coverage

After implementation, verify tests contribute to existing requirement coverage:
```bash
python scripts/req_coverage.py --detail | grep -E "REQ-YG-024|REQ-YG-040"
```

## Marketing Story (Enhanced)

> **From 4000 Lines to 100 — With Full Test Coverage**
>
> We ported a 4000-line Python novel generator to YAMLGraph:
> - 7 YAML prompts
> - 80-line graph definition
> - 4 integration tests with requirement tracing
> - A junior developer can understand the entire pipeline
>
> The same TDD discipline that built YAMLGraph core was applied to this example.

**Checklist:**
- [ ] Create test file with failing tests (red) - uses existing REQs
- [ ] Create graph.yaml with 3 phases (commented)
- [ ] Write synopsis prompts (generate, analyze, evolve)
- [ ] Write timeline prompt
- [ ] Write prose generation prompt
- [ ] Write review prompts
- [ ] Create Pydantic schemas
- [ ] Run tests - all pass (green)
- [ ] Refactor if needed
- [ ] Verify RTM coverage
- [ ] Write README with success story narrative
- [ ] Add to examples index

## Dependencies

- None (all features exist)

## Related

- [plan-research-novel-generator.md](../docs/plan-research-novel-generator.md) - Full research document
- [examples/demos/innovation_matrix/](../examples/demos/innovation_matrix/) - Similar demo already ported
- REQ-YG-024, REQ-YG-040, REQ-YG-041 - Map node requirements
