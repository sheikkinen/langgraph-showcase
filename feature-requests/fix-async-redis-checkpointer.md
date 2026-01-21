# Feature Request: Fix AsyncRedisSaver Initialization in Async Mode

**Status: ✅ IMPLEMENTED in v0.3.10**

## Summary

Fixed `AsyncRedisSaver.from_conn_string()` returning a context manager instead of a saver instance. Also added `redis-simple` checkpointer type for Upstash/Fly.io compatibility.

## Solution (v0.3.10)

1. **Sync Redis**: Uses direct instantiation `RedisSaver(redis_url=url)` instead of `from_conn_string()`
2. **Async Redis**: New `get_checkpointer_async()` function with proper `await saver.asetup()`
3. **redis-simple type**: New `SimpleRedisCheckpointer` for plain Redis (no Redis Stack required)
4. **Deprecated**: `async_mode=True` parameter on `get_checkpointer()`

## Files Changed

- `yamlgraph/storage/checkpointer_factory.py` - Fixed Redis init, added async factory
- `yamlgraph/storage/simple_redis.py` - New SimpleRedisCheckpointer class
- `yamlgraph/executor_async.py` - Made `compile_graph_async()` properly async
- `reference/checkpointers.md` - Updated docs

---

## Original Problem

When using `async_mode=True` with Redis checkpointer, `get_checkpointer()` returns an uninitialized `AsyncRedisSaver` context manager instead of an active checkpointer instance.

**Error:**
```
TypeError: Invalid checkpointer provided. Expected an instance of `BaseCheckpointSaver`, `True`, `False`, or `None`. Received _AsyncGeneratorContextManager.
```

**Location:** `yamlgraph/storage/checkpointer_factory.py` lines 62-73

## Related Issue: Upstash/Fly.io Redis Compatibility

**Important:** Even after fixing this issue, `langgraph-checkpoint-redis` will NOT work with Fly.io's Upstash Redis because:

1. `langgraph-checkpoint-redis` requires **Redis Stack** (RediSearch + RedisJSON modules)
2. Upstash Redis does NOT support Redis Stack modules
3. The questionnaire-api already has a workaround in `src/questionnaire/recap/checkpointer.py` that falls back to `MemorySaver`
4. There's a separate feature request `002-redis-checkpointer.md` for a custom checkpointer that works with plain Redis

**Implication:** For production on Fly.io with Upstash, the correct fix is:
- Either fall back to `MemorySaver` (current behavior in recap/checkpointer.py)
- Or implement the custom `RedisCheckpointer` from feature request 002

## Root Cause

```python
# Current code (broken)
if async_mode:
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver
    
    saver = AsyncRedisSaver.from_conn_string(
        url,
        ttl={"default_ttl": ttl},
    )
    # For async, caller must await saver.asetup()  <-- Comment says it, but doesn't do it!
```

The `AsyncRedisSaver.from_conn_string()` returns an async context manager (`_AsyncGeneratorContextManager`). It must be entered before use:

```python
# How it should be used
async with AsyncRedisSaver.from_conn_string(url, ttl=...) as saver:
    # saver is now usable
```

Or:
```python
saver = await AsyncRedisSaver.from_conn_string(url, ttl=...).__aenter__()
```

## Proposed Solutions

### Option 1: Make `get_checkpointer()` async (Breaking Change)

```python
async def get_checkpointer(config: dict | None, *, async_mode: bool = False) -> BaseCheckpointSaver | None:
    """..."""
    if cp_type == "redis":
        if async_mode:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver
            
            saver = AsyncRedisSaver.from_conn_string(url, ttl={"default_ttl": ttl})
            await saver.asetup()  # Initialize the connection
            return saver
        # ... sync path unchanged
```

**Impact:**
- `compile_graph_async()` must become `async def`
- `load_and_compile_async()` already is async, so minimal change

### Option 2: Return MemorySaver Fallback When URL Empty (Non-Breaking)

```python
def get_checkpointer(config: dict | None, *, async_mode: bool = False):
    if cp_type == "redis":
        url = expand_env_vars(config.get("url", ""))
        
        # If URL is empty/unset, fall back to MemorySaver
        if not url or url == "${REDIS_URL}":
            from langgraph.checkpoint.memory import MemorySaver
            import logging
            logging.getLogger(__name__).warning(
                "REDIS_URL not set, falling back to MemorySaver (not persistent)"
            )
            return MemorySaver()
        
        # ... rest of redis logic
```

**Impact:** 
- No breaking changes
- Graph config with redis works in dev without REDIS_URL set
- Clear warning about non-persistence

### Option 3: Use `True` for Deferred Checkpointer (LangGraph Feature)

LangGraph supports `checkpointer=True` to defer checkpointer creation:

```python
# In compile_graph_async, if Redis not available:
return graph.compile(checkpointer=True)  # Uses default in-memory
```

## Recommendation

**Option 2** is the safest:
- Non-breaking change
- Better DX: graphs work in dev without Redis
- Clear logging when fallback is used
- Production still requires REDIS_URL to be set

Combine with **Option 1** in a future version for proper async Redis support.

## Test Case

```python
# In dev (no REDIS_URL):
app = await load_and_compile_async("graphs/interview.yaml")
# Should work with MemorySaver fallback + warning

# In production (REDIS_URL set):
app = await load_and_compile_async("graphs/interview.yaml")  
# Should use AsyncRedisSaver properly initialized
```

## Files to Modify

1. `yamlgraph/storage/checkpointer_factory.py` - Add fallback logic
2. `yamlgraph/executor_async.py` - (Option 1 only) Make `compile_graph_async` async

## Priority

**High** - This blocks all `/v1/questionnaire` calls when graph.yaml specifies Redis checkpointer.

---

## How to Reproduce

### 1. Environment Setup
```bash
# Start local Redis
redis-cli ping  # Should return PONG

# Set environment
export REDIS_URL=redis://localhost:6379
export WEBHOOK_API_KEY=dev-key
```

### 2. Graph Configuration
`graphs/interview.yaml`:
```yaml
checkpointer:
  type: redis
  url: "${REDIS_URL}"
  ttl: 60
```

### 3. Start Server
```bash
cd questionnaire-api
PYTHONPATH=src WEBHOOK_API_KEY=dev-key REDIS_URL=redis://localhost:6379 \
  uvicorn src.api.main:app --reload --port 8000
```

### 4. Trigger Error
```bash
curl -s -X POST -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"session_id": "test", "template": "audit", "query": ""}' \
  http://127.0.0.1:8000/v1/questionnaire
```

### 5. Expected Error
```
TypeError: Invalid checkpointer provided. Expected an instance of 
`BaseCheckpointSaver`, `True`, `False`, or `None`. 
Received _AsyncGeneratorContextManager.
```

---

## Verified Findings

1. **Redis IS running** - `redis-cli ping` returns `PONG`
2. **REDIS_URL IS set** - Environment variable correctly configured
3. **Error persists** - Same error with or without REDIS_URL
4. **Root cause confirmed** - `AsyncRedisSaver.from_conn_string()` returns async context manager

---

## Workaround (Temporary)

Change `graphs/interview.yaml`:
```yaml
checkpointer:
  type: memory  # Changed from: redis
  # url: "${REDIS_URL}"  # Commented out
  # ttl: 60
```

This allows `/v1/questionnaire` to work but loses Redis persistence.

---

## How to Verify Fix

After implementing the fix:

```bash
# 1. Restore redis checkpointer in graphs/interview.yaml
# 2. Start server with REDIS_URL
PYTHONPATH=src WEBHOOK_API_KEY=dev-key REDIS_URL=redis://localhost:6379 \
  uvicorn src.api.main:app --reload --port 8000

# 3. Test v1 questionnaire endpoint
curl -s -X POST -H "x-api-key: dev-key" -H "Content-Type: application/json" \
  -d '{"session_id": "test-redis", "template": "audit", "query": ""}' \
  http://127.0.0.1:8000/v1/questionnaire | jq .

# Expected: 200 OK with opening message, no TypeError

# 4. Verify Redis persistence
redis-cli keys "*test-redis*"
# Expected: Keys exist for the session
```
