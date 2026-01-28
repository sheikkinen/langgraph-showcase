# Feature Request: YamlGraph Web UI (Studio)

**Priority:** MEDIUM  
**Type:** Feature  
**Status:** Proposed  
**Effort:** 5-7 days  
**Requested:** 2026-01-28

## Summary

Build a web-based UI for YamlGraph that visualizes graphs, shows real-time execution status, and displays tool usage - similar to LangGraph Studio but open-source and lightweight.

## Problem

Currently, YamlGraph offers:
- CLI for running graphs (`yamlgraph graph run`)
- Mermaid diagram export (`yamlgraph graph mermaid`)
- LangSmith integration for tracing (requires external service)

What's missing:
1. **No visual graph editor** - Can't see graph structure interactively
2. **No execution monitoring** - No real-time view of which node is running
3. **No tool inspection** - Can't see tool calls and responses in-flight
4. **No state viewer** - Can't inspect state between nodes

LangGraph Studio requires Enterprise license. YamlGraph should have a free, self-hosted alternative.

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YamlGraph Web UI                         │
├─────────────────────────────────────────────────────────────┤
│  Browser (Vue/React/HTMX)                                   │
│  ├── Graph Visualization (Mermaid/D3/Cytoscape)             │
│  ├── Execution Panel (SSE streaming)                        │
│  ├── State Inspector                                        │
│  └── Tool Usage Log                                         │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Backend                                            │
│  ├── GET  /api/graphs               List available graphs   │
│  ├── GET  /api/graphs/{name}        Get graph config        │
│  ├── GET  /api/graphs/{name}/mermaid Get Mermaid diagram    │
│  ├── POST /api/runs                 Start new run           │
│  ├── GET  /api/runs/{id}/stream     SSE execution events    │
│  ├── GET  /api/runs/{id}/state      Get current state       │
│  └── POST /api/runs/{id}/resume     Resume after interrupt  │
├─────────────────────────────────────────────────────────────┤
│  YamlGraph Core + Event Emitter                             │
│  ├── Graph Loader                                           │
│  ├── Node Execution with callbacks                          │
│  └── SQLite/Redis Checkpointer                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

#### 1. Graph Visualization

```
┌─────────────────────────────────────────────┐
│  reflexion-demo.yaml                    [▶] │
├─────────────────────────────────────────────┤
│                                             │
│         ┌──────────┐                        │
│         │  START   │                        │
│         └────┬─────┘                        │
│              │                              │
│         ┌────▼─────┐                        │
│         │  draft   │ ← Current (pulsing)    │
│         └────┬─────┘                        │
│              │                              │
│         ┌────▼─────┐                        │
│         │ critique │ ✓ Completed            │
│         └────┬─────┘                        │
│              │                              │
│         ┌────▼─────┐                        │
│         │  refine  │ ○ Pending              │
│         └──────────┘                        │
│                                             │
└─────────────────────────────────────────────┘
```

- Interactive Mermaid or Cytoscape.js graph
- Node states: pending, running (animated), completed, error
- Click node to see details

#### 2. Execution Panel (SSE Streaming)

```
┌─────────────────────────────────────────────┐
│  Execution Log                              │
├─────────────────────────────────────────────┤
│  09:46:23 ▶ Node: draft                     │
│  09:46:23   Provider: mistral               │
│  09:46:33 ✓ draft completed (10.0s)         │
│  09:46:33 ▶ Node: critique                  │
│  09:46:49 ✓ critique completed (16.8s)      │
│            score: 0.72                      │
│  09:46:49 ▶ Node: refine (loop iteration 1) │
│  ...                                        │
└─────────────────────────────────────────────┘
```

- Real-time log via Server-Sent Events
- Show node entry/exit with timing
- Show structured output (score, etc.)

#### 3. State Inspector

```
┌─────────────────────────────────────────────┐
│  State                                      │
├─────────────────────────────────────────────┤
│  topic: "benefits of open source"           │
│  current_draft:                             │
│    content: "Open source software..."       │
│    word_count: 487                          │
│  critique:                                  │
│    score: 0.72                              │
│    feedback: "Good structure but..."        │
│  _loop_counts:                              │
│    critique: 2                              │
│    refine: 1                                │
└─────────────────────────────────────────────┘
```

- JSON tree view of current state
- Highlight changes between nodes
- Collapsible sections for large objects

#### 4. Tool Usage Log

```
┌─────────────────────────────────────────────┐
│  Tool Calls                                 │
├─────────────────────────────────────────────┤
│  09:47:02 🔧 web_search                     │
│    query: "LangGraph vs LangChain"          │
│    → 5 results (1.2s)                       │
│  09:47:05 🔧 execute_code                   │
│    code: "print(2+2)"                       │
│    → stdout: "4" (0.1s)                     │
└─────────────────────────────────────────────┘
```

- Log all tool invocations
- Show input parameters and outputs
- Timing and success/failure status

### Implementation Plan

#### Phase 1: Backend API (2 days)

```python
# yamlgraph/web/app.py
from fastapi import FastAPI
from yamlgraph.web.routes import graphs, runs

app = FastAPI(title="YamlGraph Studio")
app.include_router(graphs.router, prefix="/api/graphs")
app.include_router(runs.router, prefix="/api/runs")
```

**Endpoints:**
- `GET /api/graphs` - List graphs from `graphs/` directory
- `GET /api/graphs/{name}` - Get graph config + mermaid
- `POST /api/runs` - Start execution, return run_id
- `GET /api/runs/{id}/stream` - SSE event stream
- `GET /api/runs/{id}/state` - Current state snapshot
- `POST /api/runs/{id}/resume` - Resume after interrupt

**Event Types:**
```python
class ExecutionEvent(BaseModel):
    type: Literal["node_start", "node_end", "tool_call", "tool_result", "error", "complete"]
    node: str | None
    timestamp: datetime
    data: dict
```

#### Phase 2: Event Emitter Integration (1 day)

Add callbacks to node execution:

```python
# yamlgraph/events.py
class EventEmitter:
    def __init__(self):
        self._listeners: list[Callable] = []
    
    def emit(self, event: ExecutionEvent) -> None:
        for listener in self._listeners:
            listener(event)
    
    def on_node_start(self, node_name: str, state: dict) -> None:
        self.emit(ExecutionEvent(type="node_start", node=node_name, data={"state_keys": list(state.keys())}))
```

Integrate into `node_compiler.py` and `llm_nodes.py`.

#### Phase 3: Frontend (2-3 days)

**Option A: HTMX + Mermaid (simpler)**
- Server-rendered HTML
- Mermaid.js for graph visualization
- SSE for live updates
- No build step

**Option B: Vue/React + Cytoscape.js (richer)**
- SPA with hot reload
- Cytoscape.js for interactive graph
- Better UX for complex graphs
- Requires build tooling

**Recommendation:** Start with HTMX for simplicity, upgrade later if needed.

```html
<!-- templates/studio.html -->
<div id="graph-view">
  <div id="mermaid-graph" hx-get="/api/graphs/{{name}}/mermaid" hx-trigger="load"></div>
</div>

<div id="execution-log" hx-ext="sse" sse-connect="/api/runs/{{run_id}}/stream">
  <div sse-swap="node_start">...</div>
  <div sse-swap="node_end">...</div>
</div>

<div id="state-view" hx-get="/api/runs/{{run_id}}/state" hx-trigger="every 2s"></div>
```

#### Phase 4: CLI Integration (0.5 day)

```bash
# Start web UI
yamlgraph studio

# Start with specific port
yamlgraph studio --port 8080

# Open browser automatically
yamlgraph studio --open
```

### Directory Structure

```
yamlgraph/
├── web/
│   ├── __init__.py
│   ├── app.py              # FastAPI app factory
│   ├── routes/
│   │   ├── graphs.py       # Graph listing/info
│   │   └── runs.py         # Execution management
│   ├── events.py           # Event emitter
│   ├── static/
│   │   ├── styles.css
│   │   └── htmx.min.js
│   └── templates/
│       ├── base.html
│       ├── index.html      # Graph list
│       ├── studio.html     # Main studio view
│       └── components/
│           ├── graph.html
│           ├── log.html
│           └── state.html
├── cli/
│   └── studio_commands.py  # yamlgraph studio command
```

## Acceptance Criteria

- [ ] `yamlgraph studio` starts web UI on localhost:8000
- [ ] Lists all graphs from `graphs/` directory
- [ ] Displays Mermaid diagram for selected graph
- [ ] Run graph with input variables from UI
- [ ] Real-time node execution updates via SSE
- [ ] State inspector shows current state
- [ ] Tool calls logged with inputs/outputs
- [ ] Handle interrupts with UI for user input
- [ ] Works with SQLite and Redis checkpointers
- [ ] Mobile-responsive layout
- [ ] No external dependencies (self-contained)

## Alternatives Considered

### 1. LangSmith Integration Only (Rejected)
Requires external service, not self-hosted, Enterprise for full features.

### 2. Jupyter Notebook Widget (Rejected)
Limited to notebook environment, not suitable for production monitoring.

### 3. CLI TUI with Rich (Partial)
Good for terminal-only, but lacks graph visualization and state inspection.

## Dependencies

- `fastapi` - Already a dependency
- `sse-starlette` - SSE support for FastAPI
- `jinja2` - Already a dependency
- HTMX/Mermaid.js - Bundled as static files

## Related

- `reference/web-ui-api.md` - Existing patterns
- `examples/npc/api/` - HTMX example
- `examples/booking/` - FastAPI example
- LangGraph Studio - Inspiration (but Enterprise-only)
