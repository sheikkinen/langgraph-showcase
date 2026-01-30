# Feature Request: Questionnaire Generation Pipeline

**Priority:** MEDIUM  
**Type:** Feature  
**Status:** Proposed  
**Effort:** 4–7 days  
**Requested:** 2026-01-30

## Summary

Add an end-to-end pipeline that generates a runnable YAMLGraph questionnaire from a topic prompt by (optionally) researching reference material, producing a structured questionnaire spec, compiling it into YAMLGraph, linting for safety/quality, running simulations/validation, and iterating automatically until acceptance criteria are met.

## Problem

Creating high-quality questionnaires is time-consuming and error-prone:

- Authors must research best practices, structure sections, craft neutral question wording, and ensure critical clauses (e.g., consent revocation, safety) are present.
- YAMLGraph questionnaires need consistent state schemas, node patterns, and validation behavior (interrupt/recap/confirm).
- Without automation, regressions happen (missing required fields, ambiguous wording, coercive phrasing, broken flow).
- Teams need a repeatable "compiler toolchain" that turns intent into a validated graph with a predictable quality bar.

## Proposed Solution

Introduce a `questionnaire_gen` pipeline that accepts a topic and configuration, then produces:

1. Reference bundle (optional websearch/RAG)
2. Questionnaire spec (typed questions, sections, constraints)
3. Compiled YAMLGraph graph(s)
4. Lint report (quality/safety checks)
5. Runnable simulation traces
6. Iterative regeneration of failing sections until the graph validates

### Components

| Component | Description |
|-----------|-------------|
| **CLI Command** | `yamlgraph questionnaire generate <topic> [options]` |
| **Pipeline Graph** | `examples/questionnaire_gen/graph.yaml` |
| **Outputs** | `dist/<slug>/questionnaire_spec.yaml`, `graph.yaml`, `lint.json`, `simulation.json`, `references.json` |

### Configuration Options

| Option | Description |
|--------|-------------|
| `--reference` | Enable web research (on/off) |
| `--tone` | Output tone (formal/clinical/friendly/legal) |
| `--risk-profile` | Lint strictness + required clauses (low/medium/high) |
| `--sections` | Override/seed sections |
| `--max-iters` | Iteration budget |
| `--provider-policy` | Cost router usage for cheap/expensive steps |

### Example Usage (CLI)

```bash
yamlgraph questionnaire generate \
  -v 'topic=BDSM consent negotiation form' \
  -v 'tone=legal' \
  -v 'reference=true' \
  -v 'risk_profile=high' \
  -v 'max_iters=3' \
  --full
```

### Example Usage (YAML)

```yaml
# examples/questionnaire_gen/graph.yaml (sketch)
version: "1.0"
name: questionnaire_gen

state:
  topic: str
  tone: str
  reference: bool
  risk_profile: str
  max_iters: int
  references: list
  spec: dict
  compiled_graph: dict
  lint: dict
  simulations: dict
  iter: int
  passed: bool

nodes:
  expand_topic:
    type: llm
    prompt: prompts/expand_topic
    output_schema: schemas/topic_outline.json

  web_research:
    type: tool
    when: "{{ reference }}"
    tool: web_search

  synthesize_spec:
    type: llm
    prompt: prompts/synthesize_spec
    output_schema: schemas/questionnaire_spec.json

  compile_yamlgraph:
    type: tool
    tool: yamlgraph_compile

  lint_questionnaire:
    type: tool
    tool: questionnaire_lint

  simulate_runs:
    type: tool
    tool: questionnaire_simulate

  decide_iterate:
    type: router
    routes:
      - when: "{{ lint.passed and simulations.passed }}"
        next: finalize
      - when: "{{ iter < max_iters }}"
        next: regenerate_failing_sections
      - default: fail

  regenerate_failing_sections:
    type: llm
    prompt: prompts/regenerate_sections

  finalize:
    type: tool
    tool: write_outputs

  fail:
    type: tool
    tool: raise_error

edges:
  - from: START
    to: expand_topic
  - from: expand_topic
    to: web_research
  - from: web_research
    to: synthesize_spec
  - from: synthesize_spec
    to: compile_yamlgraph
  - from: compile_yamlgraph
    to: lint_questionnaire
  - from: lint_questionnaire
    to: simulate_runs
  - from: simulate_runs
    to: decide_iterate
  - from: regenerate_failing_sections
    to: compile_yamlgraph
  - from: finalize
    to: END
```

## Lint Rules (Initial Set)

### Must Include

- Revocation/stop-at-any-time clause for consent-like instruments
- Safeword/stop signal fields when `risk_profile=high`
- Aftercare/follow-up preference for consent-like instruments

### Must Avoid

- Coercive/leading phrasing patterns
- Ambiguous scales without anchors

### Must Ensure

- Required fields are reachable in flow
- Recap+confirm step exists before finalize
- Exit paths are clean and non-judgmental

## PoC Topic

As a PoC, support a "BDSM consent negotiation form (non-explicit)" template category. The generator should produce non-graphic, consent-focused content with emphasis on boundaries, safety, and revocation.

## Acceptance Criteria

- [ ] CLI command `yamlgraph questionnaire generate` generates a runnable `graph.yaml` from topic
- [ ] Optional research step can be toggled on/off (`reference=true|false`)
- [ ] Lint tool returns structured results and blocks output when failing
- [ ] Simulation runner executes at least 4 default scenarios and returns pass/fail
- [ ] Iteration loop regenerates only failing sections and re-runs lint+simulation up to `max_iters`
- [ ] Generated graph includes a recap+confirm step (human-in-the-loop) before finalization
- [ ] Tests added (unit tests for lint + compilation; integration test for full pipeline)
- [ ] Documentation updated (README section + example usage)

## Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Manual questionnaire authoring | High effort, inconsistent quality |
| Single-pass generation without lint/simulation | Fast but unreliable |
| Hardcoded templates only | Reliable but not flexible |
| RAG-only approach | Helps referencing but doesn't enforce workflow correctness |

## Related

- [examples/yamlgraph_gen/](../examples/yamlgraph_gen/) - Meta-generation + validation
- [examples/cost-router/](../examples/cost-router/) - Provider routing by complexity/cost
- [examples/fastapi_interview.py](../examples/fastapi_interview.py) - Interrupt + sessions
- [examples/book_translator/](../examples/book_translator/) - Map nodes / parallelism
- [examples/daily_digest/](../examples/daily_digest/) - Fly.io deployment patterns
