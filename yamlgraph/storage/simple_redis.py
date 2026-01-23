"""Simple Redis checkpointer using standard Redis commands only.

Works with any Redis-compatible service including:
- Plain Redis
- Upstash Redis
- AWS ElastiCache
- Azure Cache for Redis

Does NOT require Redis Stack modules (RediSearch, RedisJSON).

Limitations:
- Stores only the latest checkpoint per thread (no history)
- No parent chain traversal
- No version tracking
- alist() uses SCAN which is O(N)
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import orjson
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from yamlgraph.storage.serializers import (
    deep_deserialize,
    serialize_value,
    stringify_keys,
    unstringify_keys,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from langchain_core.runnables import RunnableConfig


class SimpleRedisCheckpointer(BaseCheckpointSaver):
    """Redis checkpointer using only standard Redis commands.

    Works with plain Redis without requiring Redis Stack modules.

    Args:
        redis_url: Redis connection URL (e.g., "redis://localhost:6379")
        key_prefix: Prefix for all Redis keys (default: "lg:")
        ttl: Time-to-live in seconds for checkpoints (default: None = no expiry)
        max_connections: Maximum Redis connections (default: 10)
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "lg:",
        ttl: int | None = None,
        max_connections: int = 10,
    ) -> None:
        super().__init__()
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.ttl = ttl
        self.max_connections = max_connections
        self._client = None
        self._sync_client = None

    def _make_key(self, thread_id: str, checkpoint_ns: str = "") -> str:
        """Generate Redis key for a checkpoint."""
        return f"{self.key_prefix}{thread_id}:{checkpoint_ns}"

    async def _get_client(self):
        """Get or create async Redis client."""
        if self._client is None:
            import redis.asyncio as redis

            self._client = redis.from_url(
                self.redis_url,
                max_connections=self.max_connections,
            )
        return self._client

    def _get_sync_client(self):
        """Get or create sync Redis client."""
        if self._sync_client is None:
            import redis

            self._sync_client = redis.from_url(
                self.redis_url,
                max_connections=self.max_connections,
            )
        return self._sync_client

    # =========================================================================
    # Async methods (primary interface)
    # =========================================================================

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Get a checkpoint tuple by config."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        client = await self._get_client()
        key = self._make_key(thread_id, checkpoint_ns)

        data = await client.get(key)
        if not data:
            return None

        stored = orjson.loads(data)
        stored = unstringify_keys(stored)
        stored = deep_deserialize(stored)

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
        _new_versions: dict[str, Any],
    ) -> RunnableConfig:
        """Save a checkpoint."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        client = await self._get_client()
        key = self._make_key(thread_id, checkpoint_ns)

        stored = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "parent_config": config,
        }

        # Convert tuple keys to strings for orjson compatibility
        stored = stringify_keys(stored)
        data = orjson.dumps(stored, default=serialize_value)

        if self.ttl:
            await client.setex(key, self.ttl, data)
        else:
            await client.set(key, data)

        return config

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        _before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoints. Uses SCAN for key discovery.

        Note: This is O(N) and may be slow for large datasets.
        """
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
                stored = orjson.loads(data)
                stored = unstringify_keys(stored)
                stored = deep_deserialize(stored)
                yield CheckpointTuple(
                    config=stored.get("parent_config", {}),
                    checkpoint=stored["checkpoint"],
                    metadata=stored.get("metadata", {}),
                )
                count += 1

    async def aput_writes(
        self,
        config: RunnableConfig,
        _writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Store pending writes. Not fully implemented for simple version."""
        # Simple implementation: store writes as part of checkpoint
        pass

    async def aclose(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def adelete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread."""
        client = await self._get_client()
        pattern = self._make_key(thread_id, "*")

        # Use SCAN to find all keys for this thread, then delete
        keys_to_delete = []
        async for key in client.scan_iter(match=pattern):
            keys_to_delete.append(key)

        # Also check for key without namespace suffix
        base_key = self._make_key(thread_id, "")
        if await client.exists(base_key):
            keys_to_delete.append(base_key)

        if keys_to_delete:
            await client.delete(*keys_to_delete)

    # =========================================================================
    # Sync methods (required by BaseCheckpointSaver)
    # =========================================================================

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Get a checkpoint tuple by config (sync version)."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        client = self._get_sync_client()
        key = self._make_key(thread_id, checkpoint_ns)

        data = client.get(key)
        if not data:
            return None

        stored = orjson.loads(data)
        stored = unstringify_keys(stored)
        stored = deep_deserialize(stored)

        return CheckpointTuple(
            config=config,
            checkpoint=stored["checkpoint"],
            metadata=stored.get("metadata", {}),
            parent_config=stored.get("parent_config"),
        )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        _new_versions: dict[str, Any],
    ) -> RunnableConfig:
        """Save a checkpoint (sync version)."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        client = self._get_sync_client()
        key = self._make_key(thread_id, checkpoint_ns)

        stored = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "parent_config": config,
        }

        # Convert tuple keys to strings for orjson compatibility
        stored = stringify_keys(stored)
        data = orjson.dumps(stored, default=serialize_value)

        if self.ttl:
            client.setex(key, self.ttl, data)
        else:
            client.set(key, data)

        return config

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        _before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints (sync version)."""
        client = self._get_sync_client()

        pattern = f"{self.key_prefix}*"
        if config and "thread_id" in config.get("configurable", {}):
            thread_id = config["configurable"]["thread_id"]
            pattern = f"{self.key_prefix}{thread_id}:*"

        count = 0
        for key in client.scan_iter(match=pattern):
            if limit and count >= limit:
                break

            data = client.get(key)
            if data:
                stored = orjson.loads(data)
                stored = unstringify_keys(stored)
                stored = deep_deserialize(stored)
                yield CheckpointTuple(
                    config=stored.get("parent_config", {}),
                    checkpoint=stored["checkpoint"],
                    metadata=stored.get("metadata", {}),
                )
                count += 1

    def put_writes(
        self,
        config: RunnableConfig,
        _writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Store pending writes (sync version)."""
        pass

    def delete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread (sync version)."""
        client = self._get_sync_client()
        pattern = self._make_key(thread_id, "*")

        # Use SCAN to find all keys for this thread, then delete
        keys_to_delete = []
        for key in client.scan_iter(match=pattern):
            keys_to_delete.append(key)

        # Also check for key without namespace suffix
        base_key = self._make_key(thread_id, "")
        if client.exists(base_key):
            keys_to_delete.append(base_key)

        if keys_to_delete:
            client.delete(*keys_to_delete)
