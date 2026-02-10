# Feature Request: Linter Cross-Reference & Semantic Checks

**ID:** 025
**Priority:** P1 - High
**Status:** ✅ Implemented (v0.4.27)
**Effort:** 3–5 days
**Requested:** 2026-02-10
**Origin:** Functional coverage audit of linter vs `reference/` documentation

## Problem

The linter validates structural correctness (node types, prompt files, tool references, state declarations, edge reachability) but does NOT cross-reference names across sections or validate expression/condition syntax. This creates 8 **silent wrong behavior** scenarios where the graph runs but produces incorrect results.

Current linter: 26 issue codes, 21 functions, all pattern types covered.
Gap: 8 HIGH-priority, 7 MEDIUM-priority missing checks.

## HIGH Priority — Silent Wrong Behavior

### 1. Edge `from`/`to` reference non-existent nodes

```yaml
edges:
  - from: START
    to: genrate      # typo — no such node
  - from: generate
    to: END
```

Edge silently dropped. `generate` becomes unreachable (W002 fires, but the root cause — the typo — is hidden).

**Suggested:** `E006` / error / `"Edge references unknown node '{name}'"`. Check both `from` and `to` targets against `nodes` keys + `START`/`END`.

**Traces:** `check_edge_coverage` builds a graph from edges but never validates that edge endpoints exist in `nodes`.

### 2. `loop_limits` reference non-existent nodes

```yaml
loop_limits:
  critiqu: 3         # typo — should be 'critique'
```

Limit silently ignored. The loop runs infinitely. No error, no warning.

**Suggested:** `E008` / error / `"loop_limits references unknown node '{name}'"`.

**Traces:** `graph_loader.py` passes `loop_limits` through without validation. No linter check exists.

### 3. Passthrough node missing `output`

```yaml
nodes:
  transform:
    type: passthrough
    # forgot output: — node does nothing
```

Node silently returns only `current_step`. User thinks state was updated.

**Suggested:** `E601` / error / `"Passthrough node '{name}' missing required 'output' field"`.

**Traces:** `node_factory/control_nodes.py` creates passthrough function that returns `{current_step: ...}` when no output mapping provided.

### 4. `tool_call` node missing required fields

```yaml
nodes:
  search:
    type: tool_call
    # missing 'tool' and 'args' — KeyError at runtime
```

`KeyError` at runtime, no indication of which YAML field is wrong.

**Suggested:** `E701` / error / `"tool_call node '{name}' missing required field 'tool'"`, `E702` for `'args'`.

**Traces:** `node_factory/tool_nodes.py` L34–35: `node_config["tool"]`, `node_config["args"]`.

### 5. Condition expression syntax validation

```yaml
edges:
  - from: critique
    to: [draft, END]
    condition: "{state.score} < 0.8"    # braces + state. prefix = WRONG
```

Condition silently fails or matches incorrectly. The documented correct syntax is bare: `score < 0.8`.

**Suggested:** `W801` / warning / `"Condition '{expr}' contains braces or 'state.' prefix — conditions use bare syntax (e.g., 'score < 0.8')"`.

**Traces:** `reference/expressions.md` documents this as a common mistake. `utils/validators.py` has `validate_condition_expression` but the linter doesn't call it.

### 6. Variable expression missing `state.` prefix

```yaml
nodes:
  draft:
    variables:
      name: "{name}"          # missing state. — treated as literal string
```

Expression `{name}` is treated as literal string `"{name}"`. User expects state substitution.

**Suggested:** `W007` / warning / `"Variable template '{expr}' looks like a state reference but missing 'state.' prefix"`.

**Traces:** `utils/expressions.py` `resolve_template` requires `{state.field}` syntax. `{name}` without `state.` passes through unchanged.

### 7. `on_error: fallback` without fallback config

```yaml
nodes:
  generate:
    type: llm
    on_error: fallback
    # missing fallback: { provider: ... } — fails only when primary provider fails
```

Error only manifests when the primary provider fails — very hard to debug.

**Suggested:** `E010` / error / `"Node '{name}' uses on_error: fallback but missing 'fallback' configuration"`.

**Traces:** `error_handlers.py` expects `fallback.provider` in node config.

### 8. `type: conditional` edge with string `to`

```yaml
edges:
  - from: critique
    type: conditional
    to: draft              # should be [draft, END]
```

Conditional edge silently becomes a normal edge. Routing doesn't work.

**Suggested:** `E802` / error / `"Edge with type: conditional must have 'to' as a list"`.

**Traces:** `graph_loader.py` `_process_edge` checks `isinstance(to_node, list)` — string `to` falls through to normal edge handling.

## MEDIUM Priority — Confusing Runtime Errors

### 9. Router route targets non-existent node

```yaml
nodes:
  router:
    type: router
    routes:
      positive: handle_good    # no such node
```

**Suggested:** `E104` / error / `"Router route '{route}' targets non-existent node '{target}'"`.

### 10. `data_files` reference non-existent files

**Suggested:** `E007` / error / `"data_file '{key}' references non-existent file '{path}'"`.

### 11. `exports` state key typo

**Suggested:** `W005` / warning / `"Export key '{key}' is not a known state_key from any node"`.

### 12. `exports` invalid format

**Suggested:** `E009` / error / `"Export format '{fmt}' not recognized. Use: markdown, json, text"`.

### 13. `requires` references unknown state keys

**Suggested:** `W006` / warning / `"Node '{name}' requires '{key}' which is not produced by any node"`.

### 14. `checkpointer.type` invalid value

**Suggested:** `E305` / error / `"Checkpointer type '{type}' not recognized. Use: memory, sqlite, redis"`.

### 15. Subgraph `mode` invalid value

**Suggested:** `W503` / warning / `"Subgraph mode '{mode}' not recognized. Use: invoke, stream"`.

## Proposed Implementation

### Phase 1: Cross-reference checks (HIGH items 1, 2, 9) — `checks.py`

Add `check_cross_references(graph_path)` that validates:
- Edge `from`/`to` → node names
- `loop_limits` keys → node names
- Router route targets → node names

All share the same logic: collect node names, check references against them.

**Effort:** ~4 hours.

### Phase 2: Node-type required fields (HIGH items 3, 4) — `patterns/`

Add `check_passthrough_patterns()` and `check_tool_call_patterns()` following existing pattern module convention.

**Effort:** ~3 hours.

### Phase 3: Expression/condition syntax (HIGH items 5, 6) — `checks.py`

Add `check_expression_syntax()` that scans:
- Edge `condition` values for braces/state. prefix
- Node `variables` values for `{name}` without `state.`

**Effort:** ~3 hours.

### Phase 4: Error handling validation (HIGH items 7, 8) — `checks.py`

Add `check_error_handling()` and `check_edge_types()`.

**Effort:** ~2 hours.

### Phase 5: MEDIUM checks (items 9–15) — `checks.py`

Enumeration validation and state-key cross-referencing.

**Effort:** ~4 hours.

## Acceptance Criteria

| # | Criterion | Test |
|---|-----------|------|
| 1 | Edge with typo in `from`/`to` → E006 | `test_edge_unknown_node_error` |
| 2 | `loop_limits` with typo → E008 | `test_loop_limits_unknown_node_error` |
| 3 | Passthrough without `output` → E601 | `test_passthrough_missing_output_error` |
| 4 | `tool_call` without `tool` → E701 | `test_tool_call_missing_tool_error` |
| 5 | Condition with braces → W801 | `test_condition_braces_warning` |
| 6 | Variable `{name}` without state. → W007 | `test_variable_missing_state_prefix_warning` |
| 7 | `on_error: fallback` without config → E010 | `test_fallback_missing_config_error` |
| 8 | Conditional edge with string `to` → E802 | `test_conditional_edge_string_to_error` |
| 9 | All existing 1524 tests still pass | Full suite |
| 10 | All existing 23 linter tests still pass | `test_graph_linter.py` |

## Related

- `yamlgraph/linter/checks.py` — Core linter checks
- `yamlgraph/linter/patterns/` — Pattern-specific validators
- `reference/graph-yaml.md` — Graph YAML specification
- `reference/expressions.md` — Expression language specification
- `tests/unit/test_graph_linter.py` — Linter tests
