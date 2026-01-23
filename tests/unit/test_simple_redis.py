"""Unit tests for SimpleRedisCheckpointer.

TDD tests for add-simple-redis-checkpointer feature.
Tests the plain Redis checkpointer that works without Redis Stack.
"""

import base64
from collections import ChainMap
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

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


class TestSerializationHelpers:
    """Test serialize_value and deserialize_value functions."""

    def test_serialize_uuid(self):
        """Should serialize UUID to dict with __type__."""
        from yamlgraph.storage.serializers import serialize_value

        uuid = UUID("12345678-1234-5678-1234-567812345678")
        result = serialize_value(uuid)
        assert result == {
            "__type__": "uuid",
            "value": "12345678-1234-5678-1234-567812345678",
        }

    def test_serialize_datetime(self):
        """Should serialize datetime to ISO format."""
        from yamlgraph.storage.serializers import serialize_value

        dt = datetime(2026, 1, 21, 12, 30, 45)
        result = serialize_value(dt)
        assert result == {"__type__": "datetime", "value": "2026-01-21T12:30:45"}

    def test_serialize_bytes(self):
        """Should serialize bytes to base64."""
        from yamlgraph.storage.serializers import serialize_value

        data = b"hello world"
        result = serialize_value(data)
        assert result["__type__"] == "bytes"
        assert base64.b64decode(result["value"]) == b"hello world"

    def test_serialize_unknown_type_raises(self):
        """Should raise TypeError for unknown types."""
        from yamlgraph.storage.serializers import serialize_value

        class CustomClass:
            pass

        with pytest.raises(TypeError, match="Cannot serialize"):
            serialize_value(CustomClass())

    def test_deserialize_uuid(self):
        """Should deserialize UUID from dict."""
        from yamlgraph.storage.serializers import deserialize_value

        data = {"__type__": "uuid", "value": "12345678-1234-5678-1234-567812345678"}
        result = deserialize_value(data)
        assert result == UUID("12345678-1234-5678-1234-567812345678")

    def test_deserialize_datetime(self):
        """Should deserialize datetime from ISO format."""
        from yamlgraph.storage.serializers import deserialize_value

        data = {"__type__": "datetime", "value": "2026-01-21T12:30:45"}
        result = deserialize_value(data)
        assert result == datetime(2026, 1, 21, 12, 30, 45)

    def test_deserialize_bytes(self):
        """Should deserialize bytes from base64."""
        from yamlgraph.storage.serializers import deserialize_value

        encoded = base64.b64encode(b"hello world").decode()
        data = {"__type__": "bytes", "value": encoded}
        result = deserialize_value(data)
        assert result == b"hello world"

    def test_deserialize_regular_dict_unchanged(self):
        """Should return regular dicts unchanged."""
        from yamlgraph.storage.serializers import deserialize_value

        data = {"name": "test", "value": 123}
        result = deserialize_value(data)
        assert result == {"name": "test", "value": 123}


class TestDeepDeserialize:
    """Test deep_deserialize function."""

    def testdeep_deserialize_nested_uuid(self):
        """Should deserialize nested UUIDs."""
        from yamlgraph.storage.serializers import deep_deserialize

        data = {
            "checkpoint": {
                "id": {
                    "__type__": "uuid",
                    "value": "12345678-1234-5678-1234-567812345678",
                },
                "name": "test",
            }
        }
        result = deep_deserialize(data)
        assert result["checkpoint"]["id"] == UUID(
            "12345678-1234-5678-1234-567812345678"
        )
        assert result["checkpoint"]["name"] == "test"

    def testdeep_deserialize_list_with_uuids(self):
        """Should deserialize UUIDs in lists."""
        from yamlgraph.storage.serializers import deep_deserialize

        data = [
            {"__type__": "uuid", "value": "12345678-1234-5678-1234-567812345678"},
            {"__type__": "datetime", "value": "2026-01-21T12:00:00"},
        ]
        result = deep_deserialize(data)
        assert result[0] == UUID("12345678-1234-5678-1234-567812345678")
        assert result[1] == datetime(2026, 1, 21, 12, 0, 0)

    def testdeep_deserialize_primitive(self):
        """Should return primitives unchanged."""
        from yamlgraph.storage.serializers import deep_deserialize

        assert deep_deserialize("hello") == "hello"
        assert deep_deserialize(123) == 123
        assert deep_deserialize(None) is None


class TestSyncMethods:
    """Test sync methods with mocked Redis client."""

    def test_put_without_ttl(self):
        """Should use set() when no TTL configured."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = MagicMock()
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._sync_client = mock_client

        config = {"configurable": {"thread_id": "test-thread"}}
        checkpoint = {"v": 1, "id": "cp-123", "ts": "2026-01-21T00:00:00Z"}
        metadata = {"source": "test"}

        saver.put(config, checkpoint, metadata, {})

        mock_client.set.assert_called_once()
        mock_client.setex.assert_not_called()

    def test_put_with_ttl(self):
        """Should use setex() when TTL configured."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = MagicMock()
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379", ttl=3600)
        saver._sync_client = mock_client

        config = {"configurable": {"thread_id": "test-thread"}}
        checkpoint = {"v": 1, "id": "cp-123", "ts": "2026-01-21T00:00:00Z"}
        metadata = {"source": "test"}

        saver.put(config, checkpoint, metadata, {})

        mock_client.setex.assert_called_once()
        # First arg is key, second is TTL, third is data
        call_args = mock_client.setex.call_args[0]
        assert call_args[1] == 3600

    def test_get_tuple_returns_none_for_missing(self):
        """Should return None when key not found."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = MagicMock()
        mock_client.get.return_value = None
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._sync_client = mock_client

        config = {"configurable": {"thread_id": "test-thread"}}
        result = saver.get_tuple(config)

        assert result is None

    def test_get_tuple_deserializes_data(self):
        """Should deserialize stored checkpoint."""
        import orjson

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        stored = {
            "checkpoint": {"v": 1, "id": "cp-123"},
            "metadata": {"source": "test"},
            "parent_config": None,
        }
        mock_client = MagicMock()
        mock_client.get.return_value = orjson.dumps(stored)
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._sync_client = mock_client

        config = {"configurable": {"thread_id": "test-thread"}}
        result = saver.get_tuple(config)

        assert result is not None
        assert result.checkpoint["id"] == "cp-123"

    def test_list_with_limit(self):
        """Should respect limit parameter."""
        import orjson

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        stored = {
            "checkpoint": {"v": 1, "id": "cp-123"},
            "metadata": {},
            "parent_config": {},
        }
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = iter(["key1", "key2", "key3"])
        mock_client.get.return_value = orjson.dumps(stored)
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._sync_client = mock_client

        config = {"configurable": {"thread_id": "test"}}
        results = list(saver.list(config, limit=2))

        assert len(results) == 2

    def test_list_with_thread_filter(self):
        """Should filter by thread_id in pattern."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = MagicMock()
        mock_client.scan_iter.return_value = iter([])
        saver = SimpleRedisCheckpointer(
            redis_url="redis://localhost:6379", key_prefix="lg:"
        )
        saver._sync_client = mock_client

        config = {"configurable": {"thread_id": "my-thread"}}
        list(saver.list(config))

        # Should use thread-specific pattern
        mock_client.scan_iter.assert_called_once()
        call_kwargs = mock_client.scan_iter.call_args[1]
        assert call_kwargs["match"] == "lg:my-thread:*"


class TestAsyncMethodsWithTTL:
    """Test async methods with TTL."""

    @pytest.mark.asyncio
    async def test_aput_with_ttl(self):
        """Should use setex() when TTL configured."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = AsyncMock()
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379", ttl=7200)
        saver._client = mock_client

        config = {"configurable": {"thread_id": "test-thread"}}
        checkpoint = {"v": 1, "id": "cp-123"}
        metadata = {}

        await saver.aput(config, checkpoint, metadata, {})

        mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_aget_tuple_returns_none_for_missing(self):
        """Should return None when key not found."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = AsyncMock()
        mock_client.get.return_value = None
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._client = mock_client

        config = {"configurable": {"thread_id": "test-thread"}}
        result = await saver.aget_tuple(config)

        assert result is None

    @pytest.mark.asyncio
    async def test_aclose_closes_client(self):
        """Should close Redis client on aclose()."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = AsyncMock()
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._client = mock_client

        await saver.aclose()

        mock_client.close.assert_called_once()
        assert saver._client is None

    @pytest.mark.asyncio
    async def test_aclose_noop_if_no_client(self):
        """Should not error if client not initialized."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        await saver.aclose()  # Should not raise


class TestChainMapSerialization:
    """Test ChainMap serialization/deserialization."""

    @pytest.mark.asyncio
    async def test_chainmap_serialization(self):
        """Should serialize and deserialize ChainMap correctly."""
        from yamlgraph.storage.serializers import (
            deserialize_value,
            serialize_value,
        )

        chainmap = ChainMap({"a": 1}, {"b": 2})
        serialized = serialize_value(chainmap)

        assert serialized == {"__type__": "chainmap", "value": {"a": 1, "b": 2}}

        deserialized = deserialize_value(serialized)
        assert isinstance(deserialized, ChainMap)
        assert dict(deserialized) == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_chainmap_in_checkpoint(self):
        """Should handle ChainMap in checkpoint state."""
        import orjson

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = AsyncMock()
        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379", ttl=60)
        saver._client = mock_client

        # Checkpoint with ChainMap
        checkpoint = {
            "v": 1,
            "ts": "2024-01-01T00:00:00Z",
            "id": "test",
            "channel_values": {"config": ChainMap({"key": "value"})},
        }
        metadata = {"source": "test"}
        config = {"configurable": {"thread_id": "test"}}

        await saver.aput(config, checkpoint, metadata, {})

        # Verify setex was called and data contains ChainMap
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args[0]  # positional args
        stored_data = call_args[2]  # third arg is data
        decoded = orjson.loads(stored_data)

        assert (
            decoded["checkpoint"]["channel_values"]["config"]["__type__"] == "chainmap"
        )
        assert decoded["checkpoint"]["channel_values"]["config"]["value"] == {
            "key": "value"
        }


class TestFunctionSerialization:
    """Test function/callable serialization handling."""

    def test_function_serialization_returns_marker(self):
        """Should serialize functions as null marker."""
        from yamlgraph.storage.serializers import serialize_value

        def my_func():
            pass

        serialized = serialize_value(my_func)
        assert serialized == {"__type__": "function", "value": None}

    def test_lambda_serialization(self):
        """Should serialize lambdas as null marker."""
        from yamlgraph.storage.serializers import serialize_value

        serialized = serialize_value(lambda x: x)
        assert serialized == {"__type__": "function", "value": None}

    def test_class_not_treated_as_function(self):
        """Classes should not be treated as functions."""
        from yamlgraph.storage.serializers import serialize_value

        class MyClass:
            pass

        # Classes should raise TypeError (not treated as callable to skip)
        import pytest

        with pytest.raises(TypeError):
            serialize_value(MyClass)


class TestTupleKeySerialization:
    """Test tuple dict key serialization/deserialization."""

    def test_tuple_key_serialization(self):
        """Should serialize tuple keys to strings."""
        from yamlgraph.storage.serializers import deserialize_key, serialize_key

        key = ("node_name", "task_id_123")
        serialized = serialize_key(key)

        assert isinstance(serialized, str)
        assert serialized.startswith("__tuple__:")

        deserialized = deserialize_key(serialized)
        assert deserialized == key

    def test_string_key_passthrough(self):
        """String keys should pass through unchanged."""
        from yamlgraph.storage.serializers import deserialize_key, serialize_key

        key = "normal_key"
        serialized = serialize_key(key)
        assert serialized == key

        deserialized = deserialize_key(key)
        assert deserialized == key

    def teststringify_keys_recursive(self):
        """Should recursively convert tuple keys in nested dicts."""
        from yamlgraph.storage.serializers import stringify_keys, unstringify_keys

        data = {
            "channel_versions": {
                ("node1", "task1"): 1,
                ("node2", "task2"): 2,
            },
            "nested": {"list": [{("key1", "key2"): "value"}]},
        }

        stringified = stringify_keys(data)

        # Check structure is preserved but keys are strings
        assert isinstance(stringified, dict)
        assert "channel_versions" in stringified
        for k in stringified["channel_versions"]:
            assert isinstance(k, str)
            assert k.startswith("__tuple__:")

        # Round-trip should restore original
        restored = unstringify_keys(stringified)
        assert restored == data

    def test_tuple_key_in_checkpoint(self):
        """Should handle tuple keys in actual checkpoint data."""
        import orjson

        from yamlgraph.storage.simple_redis import (
            serialize_value,
            stringify_keys,
            unstringify_keys,
        )

        # Simulate LangGraph checkpoint structure
        checkpoint = {
            "v": 1,
            "ts": "2024-01-01T00:00:00Z",
            "id": "test",
            "channel_versions": {
                ("__start__", "task1"): 1,
                ("node1", "task2"): 2,
            },
            "versions_seen": {
                ("node1", "task2"): {
                    "channel1": 1,
                },
            },
        }

        stored = {"checkpoint": checkpoint}

        # Stringify, serialize, deserialize, unstringify
        stringified = stringify_keys(stored)
        data = orjson.dumps(stringified, default=serialize_value)
        loaded = orjson.loads(data)
        restored = unstringify_keys(loaded)

        assert restored == stored
        assert ("__start__", "task1") in restored["checkpoint"]["channel_versions"]


class TestDeleteThread:
    """Test thread deletion functionality."""

    @pytest.mark.asyncio
    async def test_adelete_thread_removes_keys(self):
        """Should delete all keys for a thread."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = AsyncMock()
        # Mock scan_iter to return async iterator directly (not a coroutine)
        mock_client.scan_iter = MagicMock(
            return_value=AsyncIteratorMock(
                [
                    b"lg:test-thread:ns1",
                    b"lg:test-thread:ns2",
                ]
            )
        )
        mock_client.exists = AsyncMock(return_value=True)
        mock_client.delete = AsyncMock()

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._client = mock_client

        await saver.adelete_thread("test-thread")

        # Should call delete with all found keys plus base key
        mock_client.delete.assert_called_once()
        call_args = mock_client.delete.call_args[0]
        assert len(call_args) >= 1  # At least the base key

    @pytest.mark.asyncio
    async def test_adelete_thread_no_keys(self):
        """Should handle case when no keys exist."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = AsyncMock()
        mock_client.scan_iter = MagicMock(return_value=AsyncIteratorMock([]))
        mock_client.exists = AsyncMock(return_value=False)
        mock_client.delete = AsyncMock()

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._client = mock_client

        await saver.adelete_thread("nonexistent-thread")

        # Should not call delete when no keys found
        mock_client.delete.assert_not_called()

    def test_delete_thread_sync(self):
        """Should delete all keys for a thread (sync)."""
        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        mock_client = MagicMock()
        mock_client.scan_iter = MagicMock(
            return_value=[
                b"lg:test-thread:ns1",
            ]
        )
        mock_client.exists = MagicMock(return_value=True)
        mock_client.delete = MagicMock()

        saver = SimpleRedisCheckpointer(redis_url="redis://localhost:6379")
        saver._sync_client = mock_client

        saver.delete_thread("test-thread")

        mock_client.delete.assert_called_once()


class AsyncIteratorMock:
    """Helper to mock async iterators."""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item
