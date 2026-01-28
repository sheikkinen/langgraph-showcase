# Feature Request: YamlGraph Studio UI

**Priority:** ~~LOW~~ N/A  
**Type:** Feature  
**Status:** REJECTED  
**Effort:** 4-5 days  
**Requested:** 2026-01-28  
**Rejected:** 2026-01-28  
**Depends On:** FR-011a (also rejected)

## Rejection Reason

**Scope creep.** YamlGraph's mission is YAML-first pipelines, not building a visual IDE.

**LangSmith exists.** Production-ready, well-funded, actively maintained.

**Maintenance treadmill.** UI requires ongoing updates, CSS, browser testing. Users will request features (restart, edit, etc.).

**No user demand.** Aspirational feature, not requested.

---

## Original Summary

Web-based UI for observing YamlGraph execution in real-time. Visualizes graphs, streams events, inspects state.

> **Note:** This is deferred. LangSmith provides similar functionality. Consider implementing as a separate repo (`yamlgraph-studio`) or community contribution.

## Why Deferred

1. **LangSmith exists** - Production-ready observability already available
2. **Maintenance burden** - UI requires ongoing updates, CSS, browser testing
3. **Scope creep risk** - Users will request features (restart, edit, etc.)
4. **Focus dilution** - YamlGraph's mission is YAML-first pipelines, not IDEs

## If Implemented Later

### Prerequisites
- FR-011a Event Emitter must be complete
- Events flowing to `~/.yamlgraph/events/`

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  YamlGraph Studio (separate process)                                        │
│  ├── Watch event files (fsevents/inotify)                                   │
│  ├── Serve web UI on localhost:8765                                         │
│  ├── SSE stream to browser                                                  │
│  └── List/display graphs from workspace                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Browser                                                                    │
│  ├── Graph visualization (Mermaid/Cytoscape)                                │
│  ├── Execution log (SSE)                                                    │
│  ├── State inspector                                                        │
│  └── Tool usage log                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Features

1. **Graph Visualization** - Mermaid diagram with node status (pending/running/completed/error)
2. **Execution Log** - Real-time SSE stream of events
3. **State Inspector** - JSON tree view of current state
4. **Tool Usage Log** - Tool calls with inputs/outputs

### Implementation Phases

| Phase | Days | Description |
|-------|------|-------------|
| Server | 2.5 | FastAPI + SSE + file tailing |
| Frontend | 1.5 | HTMX + Mermaid templates |
| CLI | 0.5 | `yamlgraph studio` command |

### Dependencies

```toml
[project.optional-dependencies]
studio = ["sse-starlette>=2.0", "watchfiles>=0.20"]
```

### Limitations

1. **Read-only** - Cannot control execution
2. **No authentication** - Localhost only
3. **Local files only** - No distributed support

## Alternatives

| Alternative | Pros | Cons |
|-------------|------|------|
| **LangSmith** | Production-ready, full features | External service, Enterprise for full |
| **CLI TUI (Rich)** | No browser, fast | No graph visualization |
| **Jupyter Widget** | Notebook integration | Limited to notebooks |

## Related

- FR-011a: Event Emitter (prerequisite)
- `examples/npc/api/` - HTMX patterns
- `examples/booking/` - FastAPI patterns
