# Checkpointers

Checkpointers enable state persistence across graph executions. They're required for interrupt nodes and enable session resumption.

## Quick Start

```yaml
# graphs/my-graph.yaml
version: "1.0"
name: my-graph

checkpointer:
  type: memory  # In-memory (dev/testing)
  # type: sqlite
  # path: "./sessions.db"
  # type: redis
  # url: "${REDIS_URL}"
```

## Checkpointer Types

### Memory (Default)

In-memory storage. Data lost on restart. Good for development.

```yaml
checkpointer:
  type: memory
```

### SQLite

File-based persistence. Good for single-server deployments.

```yaml
checkpointer:
  type: sqlite
  path: "./sessions.db"  # Or ":memory:" for in-memory
```

### Redis

Distributed persistence. Required for multi-server deployments. Requires Redis Stack (RediSearch + RedisJSON).

```yaml
checkpointer:
  type: redis
  url: "${REDIS_URL}"  # Environment variable expansion
  ttl: 60              # TTL in minutes (default: 60)
```

**Installation:**
```bash
pip install yamlgraph[redis]
```

> **Note**: Requires Redis Stack. For Upstash, Fly.io, or plain Redis, use `redis-simple` instead.

### Redis Simple (v0.3.10+)

Plain Redis support for Upstash, Fly.io, and Redis deployments without Redis Stack modules.

```yaml
checkpointer:
  type: redis-simple
  url: "${REDIS_URL}"
  ttl: 60                    # TTL in minutes (default: 60)
  prefix: "yamlgraph"        # Key prefix (default: "yamlgraph")
  max_connections: 10        # Connection pool size (default: 10)
```

**Installation:**
```bash
pip install yamlgraph[redis-simple]
```

**Limitations vs `redis` type:**
| Feature | redis | redis-simple |
|---------|-------|--------------|
| Full checkpoint history | ✅ | ❌ (latest only) |
| Checkpoint listing | ✅ | ❌ |
| Redis Stack required | ✅ | ❌ |
| Upstash/Fly.io compatible | ❌ | ✅ |
| Serialization | pickle | orjson (safer) |

## Environment Variables

Use `${VAR}` syntax for secrets:

```yaml
checkpointer:
  type: redis
  url: "${REDIS_URL}"  # Expands to redis://user:pass@host:6379
```

## Python API

### Sync Usage

```python
from yamlgraph.graph_loader import load_graph_config, compile_graph, get_checkpointer_for_graph

config = load_graph_config("graphs/my-graph.yaml")
graph = compile_graph(config)
checkpointer = get_checkpointer_for_graph(config)

app = graph.compile(checkpointer=checkpointer)

# Use with thread_id
result = app.invoke(
    {"input": "hello"},
    {"configurable": {"thread_id": "session-123"}}
)
```

### Async Usage

```python
from yamlgraph.executor_async import load_and_compile_async, run_graph_async

# Automatically uses async-compatible checkpointer
app = await load_and_compile_async("graphs/my-graph.yaml")

result = await run_graph_async(
    app,
    {"input": "hello"},
    {"configurable": {"thread_id": "session-123"}}
)
```

### Direct Factory Usage

```python
from yamlgraph.storage import get_checkpointer

# Sync checkpointer
checkpointer = get_checkpointer({
    "type": "redis",
    "url": "redis://localhost:6379",
    "ttl": 120,
})

# Async checkpointer (v0.3.10+)
from yamlgraph.storage.checkpointer_factory import get_checkpointer_async, shutdown_checkpointers

async def main():
    checkpointer = await get_checkpointer_async({
        "type": "redis",
        "url": "redis://localhost:6379"
    })
    
    # ... use checkpointer ...
    
    # Cleanup on shutdown
    await shutdown_checkpointers()
```

## Async Mode

For async graph execution, use `get_checkpointer_async()` instead of `get_checkpointer()`:

| Type | Sync API | Async API |
|------|----------|-----------|
| memory | `MemorySaver` | `MemorySaver` (supports both) |
| sqlite | `SqliteSaver` | `MemorySaver` (fallback) |
| redis | `RedisSaver` | `AsyncRedisSaver` |
| redis-simple | `SimpleRedisCheckpointer` | `SimpleRedisCheckpointer` (supports both) |

> **Note**: SQLite async requires `aiosqlite` package. If not installed, falls back to `MemorySaver`.

## Thread ID

Every checkpointed session requires a unique `thread_id`:

```python
config = {"configurable": {"thread_id": "user-123-session-456"}}
result = app.invoke(state, config)
```

Common patterns:
- `f"user-{user_id}"` — One session per user
- `f"user-{user_id}-{uuid4()}"` — New session each time
- `f"conversation-{conversation_id}"` — Shared conversation

### CLI Usage

```bash
# Start a new session with thread ID
yamlgraph graph run examples/demos/interview/graph.yaml --thread session-123 --var input=start

# Resume the same session (checkpointer loads saved state)
yamlgraph graph run examples/demos/interview/graph.yaml --thread session-123

# Start fresh with a new thread ID
yamlgraph graph run examples/demos/interview/graph.yaml --thread session-456 --var input=start
```

**Key insight:** Same `--thread` value = resume from checkpoint. New value = fresh start.

## Session Lifecycle

```
1. First invoke: Creates checkpoint
2. Interrupt: Saves state, returns __interrupt__
3. Resume: Loads checkpoint, continues from interrupt
4. Complete: Final state saved
```

To start fresh, use a new `thread_id`.

## See Also

- [Interrupt Nodes](interrupt-nodes.md) - Human-in-the-loop patterns
- [Async Usage](async-usage.md) - Async graph execution
- [FastAPI Example](../examples/fastapi_interview.py) - Web server integration
