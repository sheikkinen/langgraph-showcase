# Feature Request: Add Simple Redis Checkpointer for Upstash/Plain Redis

**Status: ✅ IMPLEMENTED in v0.3.10**

## Summary

Added a `redis-simple` checkpointer type that works with plain Redis instances (including Upstash) without requiring Redis Stack modules.

## Solution (v0.3.10)

New `SimpleRedisCheckpointer` class using standard Redis commands only (GET, SET, SCAN, DEL).

### Usage

```yaml
checkpointer:
  type: redis-simple
  url: ${REDIS_URL}
  prefix: "yamlgraph"        # Key prefix (default: "yamlgraph")
  ttl: 60                    # TTL in minutes (default: 60)
  max_connections: 10        # Connection pool size (default: 10)
```

### Installation

```bash
pip install yamlgraph[redis-simple]
```

### Limitations

| Feature | redis | redis-simple |
|---------|-------|--------------|
| Full checkpoint history | ✅ | ❌ (latest only) |
| Checkpoint listing | ✅ | ❌ |
| Redis Stack required | ✅ | ❌ |
| Upstash/Fly.io compatible | ❌ | ✅ |
| Serialization | pickle | orjson (safer) |

## Files Added/Changed

- `yamlgraph/storage/simple_redis.py` - New SimpleRedisCheckpointer class
- `yamlgraph/storage/checkpointer_factory.py` - Added redis-simple type
- `pyproject.toml` - Added `[redis-simple]` optional dependency
- `reference/checkpointers.md` - Documentation

---

## Original Problem

The current `redis` checkpointer type uses `langgraph-checkpoint-redis` which requires:
- **RediSearch** module (for indexing)
- **RedisJSON** module (for JSON storage)

These modules are part of **Redis Stack** and are NOT available on:
- **Upstash Redis** (popular serverless Redis, used by Fly.io)
- Many managed Redis services (AWS ElastiCache, Azure Cache for Redis basic tiers)
- Standard Redis installations without Stack modules

This means users deploying to Fly.io or similar platforms cannot use Redis-based state persistence.

## Current Workaround

Users must implement their own checkpointer fallback logic:

```python
# From questionnaire-api/src/questionnaire/recap/checkpointer.py
def get_checkpointer():
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        # Can't use AsyncRedisSaver - requires Redis Stack
        logger.warning(
            "REDIS_URL is set but langgraph-checkpoint-redis requires "
            "Redis Stack which Upstash does not support. Using MemorySaver."
        )
        return MemorySaver()
    return MemorySaver()
```

## Proposed Solution

Add a new checkpointer type `redis-simple` that uses standard Redis commands only:

### YAML Configuration

```yaml
storage:
  checkpointer:
    type: redis-simple
    url: ${REDIS_URL}
    key_prefix: "yamlgraph:"  # optional, default: "lg:"
    ttl: 86400  # optional, seconds, default: no expiry
```

### Implementation

Create `yamlgraph/storage/simple_redis.py`:

```python
"""Simple Redis checkpointer using standard Redis commands only."""

import json
import pickle
from typing import Any, AsyncIterator, Optional, Sequence, Tuple
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langchain_core.runnables import RunnableConfig
import redis.asyncio as redis


class SimpleRedisCheckpointer(BaseCheckpointSaver):
    """
    Redis checkpointer using only standard Redis commands.
    
    Works with:
    - Plain Redis
    - Upstash Redis
    - Any Redis-compatible service
    
    Does NOT require:
    - RediSearch module
    - RedisJSON module
    - Redis Stack
    """
    
    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "lg:",
        ttl: Optional[int] = None,
    ):
        super().__init__()
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl
        self._client: Optional[redis.Redis] = None
    
    async def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.redis_url)
        return self._client
    
    def _make_key(self, thread_id: str, checkpoint_ns: str = "") -> str:
        return f"{self.key_prefix}{thread_id}:{checkpoint_ns}"
    
    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        
        client = await self._get_client()
        key = self._make_key(thread_id, checkpoint_ns)
        
        data = await client.get(key)
        if not data:
            return None
        
        stored = pickle.loads(data)
        return CheckpointTuple(
            config=config,
            checkpoint=stored["checkpoint"],
            metadata=stored.get("metadata", {}),
            parent_config=stored.get("parent_config"),
        )
    
    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any],
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        
        client = await self._get_client()
        key = self._make_key(thread_id, checkpoint_ns)
        
        stored = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "parent_config": config,
        }
        
        data = pickle.dumps(stored)
        if self.ttl:
            await client.setex(key, self.ttl, data)
        else:
            await client.set(key, data)
        
        return config
    
    async def alist(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoints. Uses SCAN for key discovery."""
        client = await self._get_client()
        
        pattern = f"{self.key_prefix}*"
        if config and "thread_id" in config.get("configurable", {}):
            thread_id = config["configurable"]["thread_id"]
            pattern = f"{self.key_prefix}{thread_id}:*"
        
        count = 0
        async for key in client.scan_iter(match=pattern):
            if limit and count >= limit:
                break
            
            data = await client.get(key)
            if data:
                stored = pickle.loads(data)
                yield CheckpointTuple(
                    config=stored.get("parent_config", {}),
                    checkpoint=stored["checkpoint"],
                    metadata=stored.get("metadata", {}),
                )
                count += 1
    
    async def adelete(self, config: RunnableConfig) -> None:
        """Delete a checkpoint."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        
        client = await self._get_client()
        key = self._make_key(thread_id, checkpoint_ns)
        await client.delete(key)
    
    async def aclose(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


# Factory function for checkpointer_factory.py
async def create_simple_redis_checkpointer(
    url: str,
    key_prefix: str = "lg:",
    ttl: Optional[int] = None,
) -> SimpleRedisCheckpointer:
    """Create a SimpleRedisCheckpointer instance."""
    return SimpleRedisCheckpointer(url, key_prefix, ttl)
```

### Update checkpointer_factory.py

```python
# In _create_checkpointer_async()
elif checkpointer_type == "redis-simple":
    from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer
    url = checkpointer_config.get("url") or os.getenv("REDIS_URL")
    if not url:
        raise ValueError("redis-simple checkpointer requires 'url' or REDIS_URL env var")
    return SimpleRedisCheckpointer(
        redis_url=url,
        key_prefix=checkpointer_config.get("key_prefix", "lg:"),
        ttl=checkpointer_config.get("ttl"),
    )
```

## Benefits

1. **Upstash Support**: Works with Fly.io deployments out of the box
2. **Broad Compatibility**: Works with any Redis-compatible service
3. **Minimal Dependencies**: Only requires `redis` package (already a transitive dep)
4. **Simple Implementation**: ~150 lines, easy to maintain
5. **TTL Support**: Built-in session expiration for managed deployments

## Alternatives Considered

1. **Keep in application code**: Users implement their own checkpointer
   - ❌ Duplication across projects
   - ❌ Inconsistent implementations

2. **Wait for upstream fix**: Hope `langgraph-checkpoint-redis` adds plain Redis support
   - ❌ No timeline
   - ❌ Redis Stack is their design choice

3. **Document MemorySaver workaround**: Just use in-memory state
   - ❌ State lost on restart
   - ❌ No multi-instance support

## Implementation Effort

- **Estimated Time**: 2-3 hours
- **Lines of Code**: ~200 (implementation + tests)
- **Dependencies**: None new (redis is transitive)
- **Breaking Changes**: None (additive feature)

## Related

- [fix-async-redis-checkpointer.md](./fix-async-redis-checkpointer.md) - Separate issue with AsyncRedisSaver context manager
- Upstash Redis: https://upstash.com/docs/redis/overall/rediscompatibility
- Fly.io Redis: https://fly.io/docs/reference/redis/
