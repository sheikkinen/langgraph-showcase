# FR-012-2: Deprecate Legacy CLI Commands (list-runs, trace, export)

**Priority:** MEDIUM  
**Status:** ✅ IMPLEMENTED  
**Parent:** FR-012 (Deprecate Legacy CLI)

## Summary

Deprecate remaining legacy CLI commands that depend on `YamlGraphDB` or provide marginal value over LangSmith.

## Commands to Deprecate

### 1. `yamlgraph list-runs`

**What it does:** Lists runs stored in `YamlGraphDB` (custom SQLite).

```bash
yamlgraph list-runs --limit 10
# Thread ID    Status       Updated
# abc123       completed    2026-01-28 12:00:00
```

**Problem:**
- Only lists runs saved via legacy `yamlgraph run` or `cmd_resume`
- Does NOT list runs from `yamlgraph graph run` (uses checkpointer, not YamlGraphDB)
- Useless once legacy commands are removed

**Replacement:** LangSmith UI, or query checkpointer directly:
```bash
sqlite3 ~/.yamlgraph/checkpoints.db "SELECT thread_id FROM checkpoints LIMIT 10"
```

### 2. `yamlgraph trace`

**What it does:** Shows execution trace via LangSmith API.

```bash
yamlgraph trace --run-id <id>
```

**Problem:**
- LangSmith URL is already printed after each run
- This is just a wrapper around `print_run_tree()` utility
- Marginal value - users can click the LangSmith link

**Replacement:** Click LangSmith URL in output, or use LangSmith CLI.

### 3. `yamlgraph export`

**What it does:** Exports run state from `YamlGraphDB` to JSON.

```bash
yamlgraph export --thread-id abc123 --output results.json
```

**Problem:**
- Only works with runs saved in `YamlGraphDB`
- Modern runs use checkpointer (different storage)
- Useless once legacy commands are removed

**Replacement:** 
- `yamlgraph graph run ... --export` already outputs to JSON
- Or query checkpointer directly

### 4. `cmd_run` (Dead Code)

**What it does:** Was supposed to run `yamlgraph run --topic X` but is NOT wired up in CLI.

**Problem:** Exists in `commands.py` but not exposed in `__init__.py`. Pure dead code.

**Action:** Delete without deprecation (never worked).

## Usage Analysis

```bash
grep -rn "yamlgraph list-runs\|yamlgraph trace\|yamlgraph export" examples/ reference/ docs/
```

| Command | Documented | Used in Examples | Verdict |
|---------|------------|------------------|---------|
| `list-runs` | `reference/cli.md` | No | Remove docs |
| `trace` | `reference/cli.md` | No | Remove docs |
| `export` | `reference/cli.md` | No | Remove docs |

## Dependency: YamlGraphDB

These commands depend on `YamlGraphDB`:
- `cmd_list_runs` - calls `db.list_runs()`
- `cmd_export` - calls `db.load_state()`

Once these are removed, `YamlGraphDB` can be deleted (320 lines).

## What to Remove

| Item | Lines | Location |
|------|-------|----------|
| `cmd_run` | ~45 | `yamlgraph/cli/commands.py` |
| `cmd_list_runs` | ~20 | `yamlgraph/cli/commands.py` |
| `cmd_trace` | ~20 | `yamlgraph/cli/commands.py` |
| `cmd_export` | ~15 | `yamlgraph/cli/commands.py` |
| CLI parsers | ~25 | `yamlgraph/cli/__init__.py` |
| `YamlGraphDB` | 320 | `yamlgraph/storage/database.py` |
| `test_database.py` | 145 | `tests/unit/` |
| CLI docs | ~40 | `reference/cli.md` |
| **Total** | **~630** | |

## Implementation Plan

### Phase 1: Add Deprecation Warnings (v0.4.0)

```python
def cmd_list_runs(args: Namespace) -> None:
    """List recent pipeline runs."""
    import warnings
    warnings.warn(
        "yamlgraph list-runs is deprecated. Use LangSmith UI instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    print("⚠️  DEPRECATED: Use LangSmith UI or query checkpointer directly")
    # ... existing code
```

### Phase 2: Remove All (v0.5.0)

Delete:
- `cmd_run`, `cmd_list_runs`, `cmd_trace`, `cmd_export`
- CLI parser entries
- `YamlGraphDB` and `database.py`
- `test_database.py`
- Docs in `reference/cli.md`

## Validation Checklist

- [x] No examples use `yamlgraph list-runs`
- [x] No examples use `yamlgraph trace`  
- [x] No examples use `yamlgraph export`
- [x] `cmd_run` confirmed not wired up (dead code) - DELETED
- [x] Deprecation warnings added to `cmd_list_runs`, `cmd_trace`, `cmd_export`
- [ ] Docs updated (planned for v0.5.0 removal)

## Timeline

| Version | Action |
|---------|--------|
| v0.4.0 | Add deprecation warnings to `list-runs`, `trace`, `export` |
| v0.5.0 | Remove commands, YamlGraphDB, tests, docs |

## Related

- FR-012: Parent (deprecate all legacy CLI)
- FR-012-0: ✅ Fix CLI checkpointer
- FR-012-1: ✅ Deprecate legacy resume
