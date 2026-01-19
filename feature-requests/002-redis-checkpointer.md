# Feature Request: Redis Checkpointer

**ID:** 002  
**Priority:** P1 - Critical  
**Status:** ✅ Implemented  
**Effort:** 1 week  
**Requested:** 2026-01-19  
**Implemented:** 2026-01-19  
**Commit:** `3508b80`  
**Docs:** [reference/checkpointers.md](../reference/checkpointers.md)

## Summary

Add Redis-backed checkpointer for graph state persistence, enabling production deployments with multiple instances and session TTL.

## Motivation

YamlGraph uses SQLite for checkpointing, which:
- Only works with single-instance deployments
- Requires local filesystem
- Has no automatic session expiry

Production web applications need:
- Multi-instance support (load balancing)
- Session TTL for automatic cleanup
- Fast access from any server instance
- Managed infrastructure (Upstash, Redis Cloud, etc.)

**Use case:** questionnaire-api runs on Fly.io with 0-N auto-scaling instances. All instances must share session state.

## Proposed Solution

### YAML Configuration

```yaml
# graphs/interview.yaml
version: "1.0"
name: interview

checkpointer:
  type: redis
  url: "${REDIS_URL}"           # Environment variable expansion
  ttl: 3600                     # Session TTL in seconds
  prefix: "yamlgraph:"          # Redis key prefix
```

### Python API

```python
from yamlgraph.storage import RedisCheckpointer, get_checkpointer

# From config
checkpointer = get_checkpointer({
    "type": "redis",
    "url": "redis://localhost:6379",
    "ttl": 3600,
})

# Direct instantiation
checkpointer = RedisCheckpointer(
    redis_url="redis://localhost:6379",
    ttl_seconds=3600,
    key_prefix="myapp:",
)

# Use with graph
graph = load_and_compile("graphs/interview.yaml", checkpointer=checkpointer)
```

### Implementation

```python
# yamlgraph/storage/redis_checkpointer.py
import json
from typing import Any, Optional
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint
import redis.asyncio as aioredis

class RedisCheckpointer(BaseCheckpointSaver):
    """Redis-backed checkpoint storage with TTL support."""
    
    def __init__(
        self,
        redis_url: str,
        ttl_seconds: int = 3600,
        key_prefix: str = "yamlgraph:checkpoint:",
    ):
        self.redis_url = redis_url
        self.ttl = ttl_seconds
        self.prefix = key_prefix
        self._redis: Optional[aioredis.Redis] = None
    
    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def _key(self, thread_id: str, checkpoint_id: str) -> str:
        return f"{self.prefix}{thread_id}:{checkpoint_id}"
    
    def _thread_key(self, thread_id: str) -> str:
        return f"{self.prefix}{thread_id}:latest"
    
    async def aget(self, config: dict) -> Optional[Checkpoint]:
        """Get checkpoint from Redis."""
        redis = await self._get_redis()
        thread_id = config["configurable"]["thread_id"]
        
        # Get latest checkpoint ID
        latest_key = self._thread_key(thread_id)
        checkpoint_id = await redis.get(latest_key)
        
        if not checkpoint_id:
            return None
        
        # Get checkpoint data
        key = self._key(thread_id, checkpoint_id)
        data = await redis.get(key)
        
        if not data:
            return None
        
        return self._deserialize(data)
    
    async def aput(
        self,
        config: dict,
        checkpoint: Checkpoint,
        metadata: dict,
    ) -> dict:
        """Store checkpoint in Redis with TTL."""
        redis = await self._get_redis()
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        
        # Store checkpoint
        key = self._key(thread_id, checkpoint_id)
        data = self._serialize(checkpoint)
        await redis.setex(key, self.ttl, data)
        
        # Update latest pointer
        latest_key = self._thread_key(thread_id)
        await redis.setex(latest_key, self.ttl, checkpoint_id)
        
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }
    
    async def adelete(self, config: dict) -> None:
        """Delete all checkpoints for a thread."""
        redis = await self._get_redis()
        thread_id = config["configurable"]["thread_id"]
        
        # Find and delete all keys for this thread
        pattern = f"{self.prefix}{thread_id}:*"
        async for key in redis.scan_iter(match=pattern):
            await redis.delete(key)
    
    def _serialize(self, checkpoint: Checkpoint) -> str:
        return json.dumps(checkpoint, default=str)
    
    def _deserialize(self, data: str) -> Checkpoint:
        return json.loads(data)
    
    async def cleanup(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
```

### Sync Wrapper

```python
# For non-async usage
class RedisCheckpointerSync(RedisCheckpointer):
    """Synchronous wrapper for RedisCheckpointer."""
    
    def get(self, config: dict) -> Optional[Checkpoint]:
        import asyncio
        return asyncio.run(self.aget(config))
    
    def put(self, config: dict, checkpoint: Checkpoint, metadata: dict) -> dict:
        import asyncio
        return asyncio.run(self.aput(config, checkpoint, metadata))
```

## Configuration

### Environment Variables

```bash
REDIS_URL=redis://localhost:6379
# Or with auth
REDIS_URL=redis://user:password@host:6379
# Or Upstash
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
```

### Dependency

```toml
# pyproject.toml
[project.optional-dependencies]
redis = ["redis>=5.0.0"]
```

## Alternatives Considered

### 1. langgraph-checkpoint-redis
**Issue:** Requires Redis Stack (RediSearch+RedisJSON), not available on Upstash.

### 2. PostgreSQL checkpointer
**Considered:** Could add later, but Redis better for session-style storage.

### 3. Memory + periodic flush
**Rejected:** Loses state on instance restart.

## Acceptance Criteria

- [ ] `RedisCheckpointer` class implemented
- [ ] TTL-based automatic expiry works
- [ ] Multi-instance concurrent access safe
- [ ] Works with Upstash Redis (no Redis Stack)
- [ ] YAML `checkpointer:` config supported
- [ ] Environment variable expansion in URLs
- [ ] Cleanup method for connection management
- [ ] Integration test with real Redis
- [ ] Documentation with examples

## Related

- Feature #001: Interrupt Node (depends on checkpointing)
- Feature #005: Session Manager (builds on this)
- questionnaire-api Redis usage: src/api/sessions/redis.py
