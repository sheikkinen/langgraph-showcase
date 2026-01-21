"""Unit tests for SimpleRedisCheckpointer.

TDD tests for add-simple-redis-checkpointer feature.
Tests the plain Redis checkpointer that works without Redis Stack.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSimpleRedisCheckpointerInit:
    """Test SimpleRedisCheckpointer initialization."""

    def test_import_simple_redis_checkpointer(self):
        """SimpleRedisCheckpointer should be importable."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        assert SimpleRedisCheckpointer is not None

    def test_init_with_url(self):
        """Should initialize with redis_url."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert saver.redis_url == "redis://localhost:6379"

    def test_init_with_key_prefix(self):
        """Should accept key_prefix parameter."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(
            redis_url="redis://localhost:6379",
            key_prefix="myapp:",
        )
        assert saver.key_prefix == "myapp:"

    def test_init_default_key_prefix(self):
        """Default key_prefix should be 'lg:'."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert saver.key_prefix == "lg:"

    def test_init_with_ttl(self):
        """Should accept ttl parameter."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(
            redis_url="redis://localhost:6379",
            ttl=3600,
        )
        assert saver.ttl == 3600

    def test_init_default_ttl_none(self):
        """Default ttl should be None (no expiry)."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert saver.ttl is None


class TestSimpleRedisCheckpointerIsBaseCheckpointSaver:
    """Test that SimpleRedisCheckpointer inherits from BaseCheckpointSaver."""

    def test_inherits_from_base(self):
        """Should inherit from BaseCheckpointSaver."""
        from langgraph.checkpoint.base import BaseCheckpointSaver

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert isinstance(saver, BaseCheckpointSaver)


class TestSimpleRedisCheckpointerAsyncMethods:
    """Test async methods of SimpleRedisCheckpointer."""

    def test_has_aget_tuple_method(self):
        """Should have aget_tuple method."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert hasattr(saver, "aget_tuple")
        assert callable(saver.aget_tuple)

    def test_has_aput_method(self):
        """Should have aput method."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert hasattr(saver, "aput")
        assert callable(saver.aput)

    def test_has_alist_method(self):
        """Should have alist method."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert hasattr(saver, "alist")
        assert callable(saver.alist)

    def test_has_aclose_method(self):
        """Should have aclose method for cleanup."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert hasattr(saver, "aclose")
        assert callable(saver.aclose)


class TestSimpleRedisCheckpointerSyncMethods:
    """Test sync methods of SimpleRedisCheckpointer."""

    def test_has_get_tuple_method(self):
        """Should have get_tuple method."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert hasattr(saver, "get_tuple")
        assert callable(saver.get_tuple)

    def test_has_put_method(self):
        """Should have put method."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert hasattr(saver, "put")
        assert callable(saver.put)

    def test_has_list_method(self):
        """Should have list method."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        assert hasattr(saver, "list")
        assert callable(saver.list)


class TestSimpleRedisCheckpointerKeyGeneration:
    """Test key generation for Redis storage."""

    def test_make_key_with_thread_id(self):
        """Should generate key with thread_id."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(
            redis_url="redis://localhost:6379",
            key_prefix="test:",
        )
        key = saver._make_key("thread-123")
        assert key == "test:thread-123:"

    def test_make_key_with_checkpoint_ns(self):
        """Should include checkpoint_ns in key."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(
            redis_url="redis://localhost:6379",
            key_prefix="test:",
        )
        key = saver._make_key("thread-123", "ns-456")
        assert key == "test:thread-123:ns-456"


class TestSimpleRedisCheckpointerSerialization:
    """Test that SimpleRedisCheckpointer uses orjson, not pickle."""

    @pytest.mark.asyncio
    async def test_aput_uses_orjson(self):
        """Should use orjson for serialization, not pickle."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.set = AsyncMock()
        mock_client.setex = AsyncMock()

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._client = mock_client

        # Create a minimal checkpoint
        config = {"configurable": {"thread_id": "test-thread"}}
        checkpoint = {"v": 1, "id": "cp-123", "ts": "2026-01-21T00:00:00Z"}
        metadata = {"source": "test"}

        await saver.aput(config, checkpoint, metadata, {})

        # Verify set was called
        mock_client.set.assert_called_once()

        # Get the data that was passed to set
        call_args = mock_client.set.call_args
        key, data = call_args[0]

        # Data should be bytes (from orjson)
        assert isinstance(data, bytes)

        # Should be valid JSON, not pickle
        import orjson

        decoded = orjson.loads(data)
        assert "checkpoint" in decoded
        assert decoded["checkpoint"]["id"] == "cp-123"

    @pytest.mark.asyncio
    async def test_aget_tuple_uses_orjson(self):
        """Should use orjson for deserialization."""
        import orjson

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        # Prepare stored data in orjson format
        stored = {
            "checkpoint": {"v": 1, "id": "cp-123", "ts": "2026-01-21T00:00:00Z"},
            "metadata": {"source": "test"},
            "parent_config": None,
        }
        stored_bytes = orjson.dumps(stored)

        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=stored_bytes)

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._client = mock_client

        config = {"configurable": {"thread_id": "test-thread"}}
        result = await saver.aget_tuple(config)

        assert result is not None
        assert result.checkpoint["id"] == "cp-123"
