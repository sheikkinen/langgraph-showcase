# ADR-002: LangSmith Trace URL Utilities (FR-022)

**Date**: 2026-02-10
**Status**: Accepted
**Context**: FR-022 — Display LangSmith trace URL after graph execution

## Decision

Add a fail-safe tracing utility module (`yamlgraph/utils/tracing.py`) that auto-detects LangSmith configuration, injects tracers into LangGraph invocations, and surfaces trace URLs via CLI and Python API.

## Context

When running graphs with LangSmith enabled, traces were silently sent. Users had to manually navigate smith.langchain.com to find their run — violating Commandment 9 (*"instrument and trace execution"*). Three approaches were considered:

1. **Print URL inline in `cmd_graph_run`** — minimal change, but couples tracing logic to CLI and blocks API users from reuse.
2. **Dedicated `utils/tracing.py` module + CLI flag** — clean separation, reusable by both CLI and Python API consumers, testable in isolation.
3. **LangGraph callback subclass** — custom tracer that auto-prints URLs. Over-engineered; couples output formatting to the tracing layer.

Option 2 was chosen for its separation of concerns and reusability.

## Key Design Decisions

### 1. Delegate detection to LangSmith SDK

`is_tracing_enabled()` delegates to `langsmith.utils.tracing_is_enabled()` rather than checking env vars directly. This supports both current (`LANGCHAIN_TRACING_V2`, `LANGSMITH_API_KEY`) and legacy (`LANGCHAIN_TRACING`, `LANGCHAIN_API_KEY`) variable names without maintaining a parallel mapping.

### 2. Fail-safe contract

All five public functions (`is_tracing_enabled`, `create_tracer`, `get_trace_url`, `share_trace`, `inject_tracer_config`) return `None` on error and never raise exceptions. Tracing is observability — it must never break the pipeline it observes.

### 3. `--share-trace` CLI flag

Public URL sharing is opt-in via `--share-trace`. Without it, only the authenticated (private) trace URL is shown. This prevents accidental exposure of proprietary execution traces.

### 4. Lazy imports

`langchain_core.tracers.LangChainTracer` and `langsmith.utils` are imported inside functions, not at module level. This avoids import errors when LangSmith is not installed and keeps the module zero-cost when tracing is disabled.

## Implementation

```
yamlgraph/utils/tracing.py        — 5 functions, 116 lines
yamlgraph/cli/__init__.py          — --share-trace flag
yamlgraph/cli/graph_commands.py    — tracer injection + URL printing
yamlgraph/__init__.py              — top-level API exports
tests/unit/test_tracing.py         — 19 unit tests (all mocked)
tests/unit/test_graph_commands.py  — 6 CLI integration tests
```

### API surface

| Function | Returns | Purpose |
|---|---|---|
| `is_tracing_enabled()` | `bool` | Detect LangSmith configuration |
| `create_tracer(project_name)` | `LangChainTracer \| None` | Create tracer if enabled |
| `get_trace_url(tracer)` | `str \| None` | Authenticated trace URL |
| `share_trace(tracer)` | `str \| None` | Public shareable URL |
| `inject_tracer_config(config, tracer)` | `dict` | Add tracer to callbacks list |

### Requirement

REQ-YG-047 in ARCHITECTURE.md, Capability 13 (LangSmith Tracing).

## Consequences

- **Positive**: Trace URLs are immediately visible after every invocation. Public sharing is one flag away. API users get the same utilities. Zero overhead when tracing is disabled.
- **Negative**: Adds `langsmith` as an implicit runtime dependency (already present via `langchain`). The `share_run` API call adds ~200ms latency when `--share-trace` is used.
- **Supersedes**: No prior tracing integration existed.
