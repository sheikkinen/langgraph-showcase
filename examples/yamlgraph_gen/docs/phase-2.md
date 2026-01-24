# Phase 2: Clarification & Error Paths

> Add the `clarify_request` node and explicit error handling paths.

## Overview

Improve UX with clarification for ambiguous requests and clear error reporting.

## Prerequisites

- [x] Phase 0 complete: tools tested
- [x] Phase 1 complete: basic generator working

## Deliverables

| Deliverable | Description |
|-------------|-------------|
| Router node with `unclear` route | Detect ambiguous requests |
| `clarify_request` interrupt node | Ask user for clarification |
| Error reporting nodes | For structure/lint failures |
| Streaming status messages | Progress at each phase |

## Graph Changes

### Add Clarification Route

```yaml
edges:
  - from: classify_patterns
    conditions:
      - if: "classification.confidence < 0.7"
        to: clarify_request
      - if: "classification.patterns"
        to: load_snippets

  - from: clarify_request
    to: classify_patterns  # Re-classify with clarification
```

### Add Error Branches

```yaml
edges:
  - from: validate_structure
    conditions:
      - if: "structure_valid == true"
        to: lint_graph
      - if: "structure_valid == false"
        to: report_structure_error

  - from: lint_graph
    conditions:
      - if: "lint_result.valid == true"
        to: report_result
      - if: "lint_result.valid == false"
        to: report_lint_error
```

### Add Streaming Messages

```yaml
nodes:
  select_snippets:
    type: llm
    prompt: select_snippets
    state_key: selected_snippets
    stream_message: "🧩 Selecting snippets..."

  assemble_graph:
    type: llm
    prompt: assemble_graph
    state_key: assembled_graph
    stream_message: "📐 Assembling graph..."

  generate_prompts:
    type: llm
    prompt: generate_prompts
    state_key: generated_prompts
    stream_message: "📝 Writing prompts..."
```

## Success Criteria

- [x] Ambiguous requests trigger clarification (via router `intent` field)
- [x] Errors are clearly reported (not silent failures)
- [ ] User sees progress: "🧩 Selecting...", "📐 Assembling...", "📝 Writing..." (deferred)
- [ ] Clarification loop works (re-classify after user input) (needs testing)

## Implementation Notes

The clarification is implemented via:
1. Router node `classify_patterns` with routes: `clear` → `load_snippets`, `unclear` → `clarify_request`
2. The `intent` field in classification schema determines the route
3. `clarify_request` is an interrupt node that pauses for user input

## Test Cases

1. **Ambiguous**: "Build something for my data" → would trigger clarify (if LLM returns `intent: unclear`)
2. **Structure error**: Handled by `validate_structure` python node
3. **Lint error**: Handled by `lint_graph` python node with error reporting

## Next Phase

→ [phase-3.md](phase-3.md) - Execution Validation (COMPLETE)
