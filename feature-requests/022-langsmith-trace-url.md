# Feature Request: LangSmith Trace URL After Execution

**Priority:** MEDIUM
**Type:** Feature
**Status:** In Progress
**Effort:** 1 day
**Requested:** 2026-02-10

## Summary

Display the LangSmith trace URL after each graph invocation. Optionally share the trace publicly via `--share-trace`.

## Problem

When a user runs `yamlgraph graph run ...` with LangSmith enabled (`LANGCHAIN_TRACING_V2=true`), traces are silently sent. To find the trace, the user must open smith.langchain.com, navigate to the project, and locate the run by timestamp. This violates Commandment 9: *"instrument and trace execution."*

## Proposed Solution

### Core utility (`yamlgraph/utils/tracing.py`)

Reusable by CLI and API users:

```python
from yamlgraph.utils.tracing import create_tracer, get_trace_url, share_trace

tracer = create_tracer()  # Returns None if tracing not enabled
if tracer:
    result = app.invoke(state, config={"callbacks": [tracer]})
    print(get_trace_url(tracer))       # Authenticated URL
    print(share_trace(tracer))         # Public URL
```

### CLI integration

```bash
# Authenticated trace URL (always shown when LangSmith is configured)
yamlgraph graph run graph.yaml --var topic=AI
# 🔗 Trace: https://smith.langchain.com/o/.../projects/.../r/...

# Public shareable URL
yamlgraph graph run graph.yaml --var topic=AI --share-trace
# 🔗 Trace (public): https://smith.langchain.com/public/.../r/...
```

### Behavior

- **Auto-detect**: Only activates when `LANGCHAIN_TRACING_V2=true` AND `LANGSMITH_API_KEY` are set
- **Per-invoke**: Shows URL after each invoke (including interrupt loop iterations)
- **Fail-safe**: URL retrieval failures emit a warning, never crash the CLI
- **`--share-trace`**: Calls `client.share_run()` to make the trace publicly accessible

## Acceptance Criteria

- [ ] `yamlgraph/utils/tracing.py` with `is_tracing_enabled`, `create_tracer`, `get_trace_url`, `share_trace`
- [ ] `--share-trace` CLI flag on `graph run`
- [ ] Trace URL printed after each `invoke()` in `cmd_graph_run`
- [ ] Graceful handling when LangSmith is not configured (no output, no error)
- [ ] Graceful handling when URL retrieval fails (warning, not crash)
- [ ] Unit tests (mocked LangSmith client)
- [ ] Documentation updated (reference/cli.md)
