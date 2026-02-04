# Reflexion Demo

Self-improving essay generation with critique loop.

## Usage

```bash
yamlgraph graph run examples/demos/reflexion/graph.yaml --var topic="coffee"
```

## What It Does

1. **Draft** - Generate initial essay
2. **Critique** - LLM reviews and scores the draft
3. **Refine** - Improve based on critique
4. **Loop** - Repeat until score threshold or max iterations

## Pipeline

```
START → draft → critique ─┬→ (score < 8) → refine ──┐
                          │                          │
                          └→ (score >= 8) → END      │
                                    ↑                │
                                    └────────────────┘
```

## Key Concepts

- **Conditional edges** - Route based on LLM output
- **`loop_limit`** - Prevent infinite loops
- **Self-correction** - LLM improves its own output

## Conditional Routing

```yaml
edges:
  - from: critique
    to: refine
    condition: "{state.critique.score} < 8"
  - from: critique
    to: END
    condition: "{state.critique.score} >= 8"
```

## Loop Protection

```yaml
loop_limits:
  refine: 3  # Max 3 refinement attempts
```

## Learning Path

After [map](../map/). Next: [git-report](../git-report/) for tool-using agents.
