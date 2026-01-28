# Feature Request: YamlGraph Event Emitter

**Priority:** ~~HIGH~~ N/A  
**Type:** Feature  
**Status:** REJECTED  
**Effort:** 2 days  
**Requested:** 2026-01-28  
**Rejected:** 2026-01-28

## Rejection Reason

**Duplicates existing functionality.** LangSmith integration already provides:
- Node-level tracing
- Tool call logging  
- Error tracking
- Duration metrics
- Production-ready UI

**No user demand.** This was aspirational ("similar to LangGraph Studio"), not requested.

**Alternatives exist:**
```bash
# Debug logging (already works)
import logging
logging.basicConfig(level=logging.DEBUG)

# LangSmith (already works)
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=...
yamlgraph graph run reflexion-demo.yaml  # Traced automatically
```

**Maintenance burden.** ~500 lines of code to maintain for marginal value.

---

## Original Summary

Add an event emitter system to YamlGraph for observability, debugging, and integration with external tools (LangSmith, Datadog, custom dashboards).

## Problem

Currently, YamlGraph execution is opaque:
- No way to hook into node execution lifecycle
- No structured logging for debugging
- No metrics for performance monitoring
- Can't integrate with observability platforms without code changes

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  YamlGraph Execution                                                        │
│  ├── CLI: yamlgraph graph run                                               │
│  ├── Library: executor.run(graph, inputs)                                   │
│  └── Server: examples/booking, fastapi_interview.py                         │
│                           │                                                 │
│                           ▼ emit events                                     │
│              ┌────────────────────────────┐                                 │
│              │     Event Transports       │                                 │
│              │  ┌──────────────────────┐  │                                 │
│              │  │ FileTransport        │──┼──► ~/.yamlgraph/events/*.jsonl  │
│              │  └──────────────────────┘  │                                 │
│              │  ┌──────────────────────┐  │                                 │
│              │  │ CallbackTransport    │──┼──► Custom handlers              │
│              │  └──────────────────────┘  │                                 │
│              │  ┌──────────────────────┐  │                                 │
│              │  │ OTLPTransport (opt)  │──┼──► Jaeger/Tempo/LangSmith       │
│              │  └──────────────────────┘  │                                 │
│              └────────────────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Event Format (JSONL)

```jsonl
{"ts":"2026-01-28T09:46:23.123Z","type":"run_start","run_id":"abc123","graph":"reflexion-demo","inputs":{"topic":"AI"}}
{"ts":"2026-01-28T09:46:23.456Z","type":"node_start","run_id":"abc123","node":"draft","state_keys":["topic"]}
{"ts":"2026-01-28T09:46:33.789Z","type":"node_end","run_id":"abc123","node":"draft","duration_ms":10333}
{"ts":"2026-01-28T09:46:34.012Z","type":"tool_call","run_id":"abc123","node":"research","tool":"web_search","args":{"query":"AI"}}
{"ts":"2026-01-28T09:46:35.345Z","type":"tool_result","run_id":"abc123","tool":"web_search","duration_ms":1333}
{"ts":"2026-01-28T09:48:15.901Z","type":"run_end","run_id":"abc123","status":"complete","duration_ms":112778}
```

### Event Types

```python
class EventType(str, Enum):
    RUN_START = "run_start"       # Graph execution started
    RUN_END = "run_end"           # Graph execution completed
    NODE_START = "node_start"     # Node execution started
    NODE_END = "node_end"         # Node execution completed
    NODE_ERROR = "node_error"     # Node raised exception
    TOOL_CALL = "tool_call"       # Tool invocation started
    TOOL_RESULT = "tool_result"   # Tool returned result
    INTERRUPT = "interrupt"       # Waiting for user input
```

### Implementation

```python
# yamlgraph/events/emitter.py
from pathlib import Path
import json
import threading
from datetime import datetime, timezone
from typing import Protocol, Callable, TextIO

class EventEmitter:
    """Emits execution events to configured transports."""
    
    def __init__(self, run_id: str, transports: list["EventTransport"] | None = None):
        self.run_id = run_id
        self.transports = transports or [FileTransport()]
    
    def emit(self, event_type: str, **data) -> None:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "run_id": self.run_id,
            **data
        }
        for transport in self.transports:
            transport.send(event)

class NullEmitter:
    """No-op emitter for when events are disabled. Zero overhead."""
    
    def emit(self, event_type: str, **data) -> None:
        pass


# yamlgraph/events/transports.py
class EventTransport(Protocol):
    def send(self, event: dict) -> None: ...

class FileTransport:
    """Write events to JSONL file (thread-safe)."""
    
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path.home() / ".yamlgraph" / "events"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._file: TextIO | None = None
        self._index_file = self.base_dir / "runs.jsonl"
    
    def send(self, event: dict) -> None:
        with self._lock:
            if self._file is None:
                path = self.base_dir / f"{event['run_id']}.jsonl"
                self._file = open(path, "a")
            self._file.write(json.dumps(event) + "\n")
            self._file.flush()
            
            # Update run index on run_start/run_end
            if event["type"] in ("run_start", "run_end"):
                self._update_index(event)
    
    def _update_index(self, event: dict) -> None:
        """Append to runs.jsonl for fast run discovery."""
        with open(self._index_file, "a") as f:
            f.write(json.dumps(event) + "\n")

class CallbackTransport:
    """Call user-provided callback for each event."""
    
    def __init__(self, callback: Callable[[dict], None]):
        self.callback = callback
    
    def send(self, event: dict) -> None:
        self.callback(event)
```

### Integration Points

| File | Events |
|------|--------|
| `executor.py` | `run_start`, `run_end` |
| `executor_async.py` | `run_start`, `run_end` |
| `node_compiler.py` | `node_start`, `node_end`, `node_error` |
| `llm_nodes.py` | `tool_call`, `tool_result` |
| Graph loader | `interrupt` |

### CLI Integration

```python
# yamlgraph/cli/graph_commands.py
def cmd_run(args):
    run_id = args.run_id or f"{graph_name}-{uuid4().hex[:8]}"
    emitter = create_emitter_from_env(run_id, graph_name)
    
    if emitter:
        print(f"📡 Run ID: {run_id}", file=sys.stderr)
    
    executor = GraphExecutor(graph, emitter=emitter)
    result = executor.run(inputs)
```

### Configuration

```bash
# Enable via environment variable
export YAMLGRAPH_EVENTS=file        # File only
export YAMLGRAPH_EVENTS=file,otlp   # File + OpenTelemetry
export YAMLGRAPH_EVENTS=none        # Explicitly disable
```

```python
# Or programmatically
from yamlgraph.events import EventEmitter, FileTransport, CallbackTransport

emitter = EventEmitter(
    run_id="my-run",
    transports=[
        FileTransport(),
        CallbackTransport(lambda e: print(f"Event: {e['type']}")),
    ]
)
executor = GraphExecutor(graph, emitter=emitter)
```

### Directory Structure

```
yamlgraph/
├── events/
│   ├── __init__.py         # Public API: EventEmitter, NullEmitter, transports
│   ├── emitter.py          # EventEmitter, NullEmitter classes
│   ├── transports.py       # FileTransport, CallbackTransport, OTLPTransport
│   └── types.py            # EventType enum
```

### Use Cases

1. **Debugging** - `tail -f ~/.yamlgraph/events/abc123.jsonl`
2. **Metrics** - Count events, measure durations, track errors
3. **LangSmith** - Send via OTLPTransport
4. **Custom dashboard** - CallbackTransport to WebSocket
5. **Alerting** - Callback on `node_error` events

## Acceptance Criteria

- [ ] `EventEmitter` class with pluggable transports
- [ ] `NullEmitter` class for disabled case (zero overhead)
- [ ] `FileTransport` writes JSONL to `~/.yamlgraph/events/{run_id}.jsonl`
- [ ] `FileTransport` updates `~/.yamlgraph/events/runs.jsonl` index
- [ ] Thread-safe file writes with locking
- [ ] `CallbackTransport` for programmatic event handling
- [ ] Events emitted for: `run_start`, `run_end`, `node_start`, `node_end`, `node_error`
- [ ] Tool call events: `tool_call`, `tool_result`
- [ ] Interrupt event: `interrupt`
- [ ] CLI prints run_id to stderr when events enabled
- [ ] Enabled via `YAMLGRAPH_EVENTS=file` or programmatically
- [ ] Zero performance impact when disabled
- [ ] Unit tests for all transports
- [ ] Integration test: run graph, verify events in file

## Dependencies

### Core
- None - uses stdlib only (`json`, `threading`, `pathlib`)

### Optional
```toml
[project.optional-dependencies]
otlp = ["opentelemetry-api", "opentelemetry-sdk", "opentelemetry-exporter-otlp"]
```

## Future Work

- FR-011b: YamlGraph Studio UI (deferred)
- `yamlgraph events prune --older-than 7d`
- Async-safe transport for `executor_async.py`

## Related

- LangSmith - Production observability
- OpenTelemetry - Standard for distributed tracing
- `reference/streaming.md` - Existing streaming patterns
