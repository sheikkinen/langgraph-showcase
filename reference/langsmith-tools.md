# LangSmith Tools & Tracing Reference

Tracing utilities and tools for querying LangSmith run data.

## Available Tools

### `get_run_details_tool`

Get detailed information about a pipeline run.

```yaml
tools:
  get_run_details:
    type: python
    module: yamlgraph.tools.langsmith_tools
    function: get_run_details_tool
    description: "Get detailed info about a LangSmith run"
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `run_id` | `str` | No | Run UUID (defaults to latest) |

**Returns:**
```python
{
    "id": "019bcf62-...",
    "name": "generate",
    "status": "error",
    "error": "API Error: ...",
    "start_time": "2026-01-18T06:52:35.868Z",
    "end_time": "2026-01-18T06:52:42.500Z",
    "inputs": {...},
    "outputs": {...},
    "run_type": "chain"
}
```

---

### `get_run_errors_tool`

Get all errors from a run and its child nodes.

```yaml
tools:
  get_run_errors:
    type: python
    module: yamlgraph.tools.langsmith_tools
    function: get_run_errors_tool
    description: "Get errors from a run and its child nodes"
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `run_id` | `str` | No | Run UUID (defaults to latest) |

**Returns:**
```python
{
    "error_count": 2,
    "errors": [
        {"node": "generate", "error": "API Error", "run_type": "llm"},
        {"node": "validate", "error": "Schema mismatch", "run_type": "chain"}
    ]
}
```

---

### `get_failed_runs_tool`

List recent failed runs in the project.

```yaml
tools:
  get_failed_runs:
    type: python
    module: yamlgraph.tools.langsmith_tools
    function: get_failed_runs_tool
    description: "List recent failed runs in the project"
```

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | `int` | No | Max runs to return (default: 10) |
| `project_name` | `str` | No | Project name (defaults to current) |

**Returns:**
```python
{
    "failed_count": 3,
    "runs": [
        {"id": "019bcf62-...", "name": "generate", "error": "...", "start_time": "..."},
        ...
    ]
}
```

---

## Usage in Graphs

### Agent Node Example

```yaml
tools:
  get_run_details:
    type: python
    module: yamlgraph.tools.langsmith_tools
    function: get_run_details_tool
    description: "Get run details"

  get_run_errors:
    type: python
    module: yamlgraph.tools.langsmith_tools
    function: get_run_errors_tool
    description: "Get run errors"

  get_failed_runs:
    type: python
    module: yamlgraph.tools.langsmith_tools
    function: get_failed_runs_tool
    description: "List failed runs"

nodes:
  analyze_runs:
    type: agent
    prompt: run-analyzer/fetch_info
    tools: [get_run_details, get_run_errors, get_failed_runs]
    max_iterations: 5
    state_key: run_info
```

### Run Analyzer Graph

Pre-built graph for analyzing failed runs:

```bash
# Analyze most recent failed run
yamlgraph graph run examples/demos/run-analyzer/graph.yaml -v mode=last_failed

# Analyze specific run
yamlgraph graph run examples/demos/run-analyzer/graph.yaml -v run_id="019bcf62-..."
```

---

## Utility Functions

Lower-level functions in `yamlgraph/utils/langsmith.py`:

| Function | Description |
|----------|-------------|
| `get_run_details(run_id)` | Get run info dict |
| `get_run_errors(run_id)` | Get list of error dicts |
| `get_failed_runs(limit, project_name)` | Get list of failed run dicts |
| `get_client()` | Get LangSmith client |
| `get_project_name()` | Get current project |
| `get_latest_run_id()` | Get most recent run ID |
| `share_run(run_id)` | Create public share link |
| `get_run_url(run_id)` | Get web URL for run |

---

## Configuration

### Required Environment Variables

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=yamlgraph
```

### Optional

```bash
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

---

## See Also

- [Graph YAML Reference](graph-yaml.md)
- [CLI Reference](cli.md) (`--share-trace` flag)
- [Patterns - Self-Correction](patterns.md#self-correction-loops)

---

## Execution Tracing (FR-022)

YAMLGraph provides built-in trace URL retrieval and public sharing.
Tracing auto-detects when LangSmith is configured (via env vars or `.env`).

### CLI

```bash
# Trace URL shown automatically when LangSmith is configured
yamlgraph graph run graph.yaml --var topic=AI
# 🔗 Trace: https://smith.langchain.com/o/.../r/...

# Share trace publicly
yamlgraph graph run graph.yaml --var topic=AI --share-trace
# 🔗 Trace (public): https://smith.langchain.com/public/.../r/...
```

### Python API

```python
from yamlgraph import (
    load_and_compile,
    create_tracer,
    get_trace_url,
    inject_tracer_config,
    share_trace,
)

# Compile graph
graph = load_and_compile("graphs/hello.yaml")
app = graph.compile()

# Set up tracing (auto-detects .env / env vars, returns None if not configured)
tracer = create_tracer()
config = inject_tracer_config({}, tracer)

# Run with tracing
result = app.invoke({"name": "World"}, config=config)

# Get trace URL
print(get_trace_url(tracer))   # Authenticated URL
print(share_trace(tracer))     # Public URL (or None)
```

### API Reference

| Function | Description |
|----------|-------------|
| `is_tracing_enabled()` | Check if LangSmith is configured (delegates to langsmith SDK) |
| `create_tracer(project_name=None)` | Create `LangChainTracer` or `None` if tracing disabled |
| `get_trace_url(tracer)` | Get authenticated trace URL (fail-safe, returns `None`) |
| `share_trace(tracer)` | Make trace public, return shareable URL (fail-safe) |
| `inject_tracer_config(config, tracer)` | Add tracer to LangGraph config callbacks dict |

All functions accept `None` tracer and return `None` gracefully — no need to guard with `if tracer:`.
