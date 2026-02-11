# Feature Request: Chaplain Audit Fixes (FR-026)

**Priority:** HIGH
**Type:** Bug / Enhancement
**Status:** ✅ Implemented (v0.4.28)
**Effort:** 1 day
**Requested:** 2026-02-10

## Summary

Four findings from Chaplain code audit. One crash bug, two silent-failure asymmetries, one minor guard inconsistency.

## Findings

### Finding 1 — HIGH: `wrap_for_reducer` crashes on non-dict python return

**File:** `yamlgraph/map_compiler.py`, lines 62 & 147
**Bug:** `compile_map_node` loads python sub-nodes via `load_python_function()` (raw function) — no normalization. When the function returns a non-dict (string, number), `wrap_for_reducer` calls `result.get(state_key, result)` which raises `AttributeError`.
**Fix:** Add `isinstance(result, dict)` guard in `wrap_for_reducer` before calling `.get()`. If result is not a dict, wrap it as `{state_key: result}` (same normalization as `create_python_node`).

### Finding 2 — MEDIUM: LLM SKIP drops error details

**File:** `yamlgraph/node_factory/llm_nodes.py`, lines 185-191
**Bug:** `on_error == ErrorHandler.SKIP` returns `{state_key: None, "_skipped": True, ...}` but no `errors` list entry. Tool and python nodes use `build_skip_error_state()` which records a `PipelineError`. LLM nodes silently lose the error.
**Fix:** Call `build_skip_error_state()` from LLM SKIP handler for consistency, or manually append `PipelineError` to update dict.

### Finding 3 — MEDIUM: tool/python nodes ignore retry/fallback

**File:** `yamlgraph/tools/nodes.py`, lines 105-110; `yamlgraph/tools/python_tool.py`, lines 160-169
**Bug:** `on_error: retry` or `on_error: fallback` silently becomes `fail`. Only `skip` is handled; else-branch raises.
**Fix:** Reject at config time — add linter check E011 warning when tool/python nodes specify `on_error: retry` or `on_error: fallback` (unsupported). LLM nodes have provider abstraction needed for these; tool/python don't.

### Finding 4 — LOW: `prompts_relative` error guard too narrow

**File:** `yamlgraph/utils/prompts.py`, line 63
**Bug:** `prompts_relative=True` only raises `ValueError` if BOTH `graph_path` AND `prompts_dir` are `None`. If `prompts_dir` is set alone, silently falls through to step 2.
**Fix:** Log a warning when `prompts_relative=True` and `graph_path is None` but `prompts_dir` is set, making the fallback visible. The cascade behavior itself is correct.

## Acceptance Criteria

- [x] `wrap_for_reducer` handles non-dict returns without crash
- [x] LLM SKIP handler records `PipelineError` in `errors` list
- [x] Linter E011 warns on `on_error: retry/fallback` for tool/python nodes
- [x] `prompts_relative` logs warning on `graph_path=None` + `prompts_dir` set
- [x] TDD: failing tests written first for all fixes
- [x] All existing tests pass
- [x] `req_coverage.py --strict` passes
- [x] ARCHITECTURE.md updated with new requirement(s)

## Alternatives Considered

**Finding 3 — runtime rejection:** Raise `ValueError` at node creation instead of linting. Decided against: linter catches it earlier, before compilation.

## Related

- Chaplain audit output (`copilot -p "$(cat prompts/chaplain-audit.md)"`)
- `error_handlers.build_skip_error_state` — canonical skip-with-error pattern
- `create_python_node` (python_tool.py:155) — non-dict normalization reference
- FR-025: Linter cross-reference & semantic checks (added E010 fallback check)
