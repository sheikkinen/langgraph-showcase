# Bug: prompts_dir Not Combined with graph_path in prompts_relative Mode

**Status:** ✅ RESOLVED (v0.3.7)
**Priority:** HIGH
**Type:** Bug
**Version:** 0.3.6
**Component:** utils/prompts.py - resolve_prompt_path()
**Related:** bug-prompts-relative-executor.md (0.3.5 partial fix)

## Summary

When `prompts_relative: true` and `prompts_dir: prompts` are both set, the resolution uses `prompts_dir` directly as the base path instead of combining it with `graph_path.parent`.

## Expected Behavior

```yaml
# Graph at questionnaires/audit/graph.yaml
defaults:
  prompts_relative: true
  prompts_dir: prompts

nodes:
  generate_opening:
    prompt: opening  # Should resolve to questionnaires/audit/prompts/opening.yaml
```

When both prompts_relative and prompts_dir are set, prompts should resolve to:
`{graph_path.parent}/{prompts_dir}/{prompt_name}.yaml`

## Actual Behavior

```
Prompt not found: prompts/opening.yaml
```

The code resolves to just `{prompts_dir}/{prompt_name}.yaml` ignoring the graph_path.

## Root Cause

In `utils/prompts.py` line 60-65:

```python
# 1. Explicit prompts_dir takes precedence
if prompts_dir is not None:
    prompts_dir = Path(prompts_dir)
    yaml_path = prompts_dir / f"{prompt_name}.yaml"  # BUG: should use graph_path.parent
    if yaml_path.exists():
        return yaml_path
```

The prompts_dir check (step 1) runs BEFORE the graph-relative check (step 2), and when prompts_dir is set, it doesn't combine with graph_path.parent.

## Proposed Fix

When both prompts_relative and prompts_dir are provided, combine them:

```python
# 1. Graph-relative with explicit prompts_dir
if prompts_relative and prompts_dir is not None and graph_path is not None:
    graph_dir = Path(graph_path).parent
    yaml_path = graph_dir / prompts_dir / f"{prompt_name}.yaml"
    if yaml_path.exists():
        return yaml_path
    # Fall through if not found

# 2. Explicit prompts_dir (absolute path or CWD-relative)
if prompts_dir is not None:
    prompts_dir = Path(prompts_dir)
    yaml_path = prompts_dir / f"{prompt_name}.yaml"
    if yaml_path.exists():
        return yaml_path
```

## Changelog Entry

```markdown
## [0.3.7] - 2026-01-XX

### Fixed
- **prompts_relative + prompts_dir** - When both are set, prompts_dir is now
  resolved relative to graph_path.parent, not the current working directory
```

## Resolution (v0.3.7)

**Fixed:** 2026-01-20

### Changes Made

1. **Updated `yamlgraph/utils/prompts.py`** (resolve_prompt_path:59-85)
   - Added step 1: Graph-relative with explicit prompts_dir (combines both)
   - Reordered steps so combination happens before individual checks
   - Updated resolution order comments and docstrings

2. **Added test** in `tests/unit/test_prompts.py:267-299`
   - `test_prompts_relative_with_prompts_dir_combines_paths()`
   - Verifies that `prompts_dir="prompts"` + `prompts_relative=True`
     resolves to `{graph_path.parent}/prompts/{prompt_name}.yaml`

### New Resolution Order

1. Graph-relative + prompts_dir + graph_path: `graph_path.parent/prompts_dir/{prompt}.yaml`
2. Explicit prompts_dir: `prompts_dir/{prompt}.yaml`
3. Graph-relative + graph_path: `graph_path.parent/{prompt}.yaml`
4. Default: `PROMPTS_DIR/{prompt}.yaml`
5. Fallback: `{parent}/prompts/{basename}.yaml`

### Tests

All tests pass:
- ✅ 16/16 unit tests in `test_prompts.py`
- ✅ 2/2 integration tests in `test_colocated_prompts.py`
- ✅ 30/30 related unit tests (executor, graph_loader)
