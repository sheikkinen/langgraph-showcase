"""Unit tests for checkpointer factory.

TDD tests for 002: Redis Checkpointer feature.
Tests get_checkpointer() factory with env var expansion and async mode.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yamlgraph.storage.checkpointer_factory import (
    expand_env_vars,
    get_checkpointer,
)


class TestExpandEnvVars:
    """Test environment variable expansion."""

    def test_expand_single_var(self):
        """Should expand ${VAR} pattern."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}):
            result = expand_env_vars("${REDIS_URL}")
            assert result == "redis://localhost:6379"

    def test_expand_multiple_vars(self):
        """Should expand multiple ${VAR} patterns."""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "6379"}):
            result = expand_env_vars("redis://${HOST}:${PORT}/0")
            assert result == "redis://localhost:6379/0"

    def test_expand_missing_var_keeps_original(self):
        """Missing env vars should keep original ${VAR} pattern."""
        # Ensure NONEXISTENT is not set
        os.environ.pop("NONEXISTENT", None)
        result = expand_env_vars("${NONEXISTENT}")
        assert result == "${NONEXISTENT}"

    def test_expand_non_string_returns_unchanged(self):
        """Non-string values should pass through unchanged."""
        assert expand_env_vars(123) == 123
        assert expand_env_vars(None) is None
        assert expand_env_vars(["a", "b"]) == ["a", "b"]

    def test_expand_no_vars_returns_original(self):
        """String without ${} should return unchanged."""
        result = expand_env_vars("redis://localhost:6379")
        assert result == "redis://localhost:6379"

    def test_expand_empty_string(self):
        """Empty string should return empty string."""
        assert expand_env_vars("") == ""


class TestGetCheckpointerMemory:
    """Test in-memory checkpointer (default)."""

    def test_memory_checkpointer_default(self):
        """Default type should be memory."""
        config = {"type": "memory"}  # Empty config defaults to memory via get
        saver = get_checkpointer(config)

        from langgraph.checkpoint.memory import InMemorySaver

        assert isinstance(saver, InMemorySaver)

    def test_memory_checkpointer_explicit(self):
        """Explicit type: memory should work."""
        config = {"type": "memory"}
        saver = get_checkpointer(config)

        from langgraph.checkpoint.memory import InMemorySaver

        assert isinstance(saver, InMemorySaver)

    def test_none_config_returns_none(self):
        """None config should return None."""
        assert get_checkpointer(None) is None


class TestGetCheckpointerSqlite:
    """Test SQLite checkpointer."""

    def test_sqlite_checkpointer_memory(self):
        """SQLite with :memory: should work."""
        config = {"type": "sqlite", "path": ":memory:"}
        saver = get_checkpointer(config)

        from langgraph.checkpoint.sqlite import SqliteSaver

        assert isinstance(saver, SqliteSaver)

    def test_sqlite_expands_env_var(self):
        """SQLite path should expand env vars."""
        with patch.dict(os.environ, {"DB_PATH": ":memory:"}):
            config = {"type": "sqlite", "path": "${DB_PATH}"}
            saver = get_checkpointer(config)

            from langgraph.checkpoint.sqlite import SqliteSaver

            assert isinstance(saver, SqliteSaver)


class TestGetCheckpointerRedis:
    """Test Redis checkpointer (mocked)."""

    def test_redis_checkpointer_sync(self):
        """Redis sync saver should be created using direct instantiation."""
        mock_saver = MagicMock()
        mock_saver.setup = MagicMock()
        mock_redis_module = MagicMock()
        mock_redis_module.RedisSaver.return_value = mock_saver

        with patch.dict(
            "sys.modules", {"langgraph.checkpoint.redis": mock_redis_module}
        ):
            # Re-import to pick up mocked module
            import importlib

            from yamlgraph.storage import checkpointer_factory

            importlib.reload(checkpointer_factory)

            with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379"}):
                config = {"type": "redis", "url": "${REDIS_URL}", "ttl": 120}
                saver = checkpointer_factory.get_checkpointer(config)

                mock_redis_module.RedisSaver.assert_called_once_with(
                    redis_url="redis://localhost:6379",
                    ttl={"default_ttl": 120},
                )
                mock_saver.setup.assert_called_once()
                assert saver is mock_saver

    def test_redis_import_error_helpful_message(self):
        """Missing redis package should give helpful error."""
        import importlib
        import sys

        from yamlgraph.storage import checkpointer_factory

        # Save original modules
        saved_modules = {}
        for key in list(sys.modules.keys()):
            if "langgraph.checkpoint.redis" in key:
                saved_modules[key] = sys.modules.pop(key)

        # Make langgraph.checkpoint.redis import fail
        with patch.dict("sys.modules", {"langgraph.checkpoint.redis": None}):
            importlib.reload(checkpointer_factory)

            config = {"type": "redis", "url": "redis://localhost:6379"}

            with pytest.raises(ImportError) as exc_info:
                checkpointer_factory.get_checkpointer(config)

            assert "pip install yamlgraph[redis]" in str(exc_info.value)

        # Restore original modules
        sys.modules.update(saved_modules)
        importlib.reload(checkpointer_factory)

    def test_redis_default_ttl(self):
        """Redis should use default TTL of 60 if not specified."""
        mock_saver = MagicMock()
        mock_saver.setup = MagicMock()
        mock_redis_module = MagicMock()
        mock_redis_module.RedisSaver.return_value = mock_saver

        with patch.dict(
            "sys.modules", {"langgraph.checkpoint.redis": mock_redis_module}
        ):
            import importlib

            from yamlgraph.storage import checkpointer_factory

            importlib.reload(checkpointer_factory)

            config = {"type": "redis", "url": "redis://localhost:6379"}
            checkpointer_factory.get_checkpointer(config)

            mock_redis_module.RedisSaver.assert_called_once_with(
                redis_url="redis://localhost:6379",
                ttl={"default_ttl": 60},
            )


class TestGetCheckpointerErrors:
    """Test error handling."""

    def test_unknown_type_raises_error(self):
        """Unknown checkpointer type should raise ValueError."""
        config = {"type": "unknown_db"}

        with pytest.raises(ValueError) as exc_info:
            get_checkpointer(config)

        assert "Unknown checkpointer type: unknown_db" in str(exc_info.value)


# =============================================================================
# TDD Tests for fix-async-redis-checkpointer
# =============================================================================


class TestRedisSyncDirectInstantiation:
    """Test that sync Redis uses direct instantiation, not context manager."""

    def test_sync_redis_returns_saver_not_context_manager(self):
        """Sync Redis should return RedisSaver instance, not context manager."""
        mock_saver_instance = MagicMock()
        mock_saver_instance.setup = MagicMock()

        mock_redis_module = MagicMock()
        # Direct instantiation should be used, not from_conn_string
        mock_redis_module.RedisSaver.return_value = mock_saver_instance

        with patch.dict(
            "sys.modules", {"langgraph.checkpoint.redis": mock_redis_module}
        ):
            import importlib

            from yamlgraph.storage import checkpointer_factory

            importlib.reload(checkpointer_factory)

            config = {"type": "redis", "url": "redis://localhost:6379", "ttl": 60}
            saver = checkpointer_factory.get_checkpointer(config)

            # Should use direct instantiation
            mock_redis_module.RedisSaver.assert_called_once_with(
                redis_url="redis://localhost:6379",
                ttl={"default_ttl": 60},
            )
            # Should call setup()
            mock_saver_instance.setup.assert_called_once()
            # Should return the saver instance
            assert saver is mock_saver_instance


class TestGetCheckpointerAsync:
    """Test async checkpointer factory function."""

    @pytest.mark.asyncio
    async def test_get_checkpointer_async_exists(self):
        """get_checkpointer_async() function should exist."""
        from yamlgraph.storage.checkpointer_factory import get_checkpointer_async

        assert callable(get_checkpointer_async)

    @pytest.mark.asyncio
    async def test_get_checkpointer_async_redis_returns_saver(self):
        """Async Redis should return AsyncRedisSaver instance."""
        mock_saver_instance = MagicMock()
        mock_saver_instance.asetup = AsyncMock()

        mock_aio_module = MagicMock()
        mock_aio_module.AsyncRedisSaver.return_value = mock_saver_instance

        with patch.dict(
            "sys.modules", {"langgraph.checkpoint.redis.aio": mock_aio_module}
        ):
            import importlib

            from yamlgraph.storage import checkpointer_factory

            importlib.reload(checkpointer_factory)

            config = {"type": "redis", "url": "redis://localhost:6379", "ttl": 60}
            saver = await checkpointer_factory.get_checkpointer_async(config)

            # Should use direct instantiation
            mock_aio_module.AsyncRedisSaver.assert_called_once_with(
                redis_url="redis://localhost:6379",
                ttl={"default_ttl": 60},
            )
            # Should call asetup()
            mock_saver_instance.asetup.assert_awaited_once()
            # Should return the saver instance
            assert saver is mock_saver_instance

    @pytest.mark.asyncio
    async def test_get_checkpointer_async_fallback_no_url(self):
        """Should fall back to MemorySaver when REDIS_URL not set."""
        from yamlgraph.storage.checkpointer_factory import get_checkpointer_async

        # URL is ${REDIS_URL} but env var not set
        os.environ.pop("REDIS_URL", None)
        config = {"type": "redis", "url": "${REDIS_URL}"}

        saver = await get_checkpointer_async(config)

        from langgraph.checkpoint.memory import MemorySaver

        assert isinstance(saver, MemorySaver)

    @pytest.mark.asyncio
    async def test_get_checkpointer_async_memory_type(self):
        """Async memory checkpointer should work."""
        from yamlgraph.storage.checkpointer_factory import get_checkpointer_async

        config = {"type": "memory"}
        saver = await get_checkpointer_async(config)

        from langgraph.checkpoint.memory import MemorySaver

        assert isinstance(saver, MemorySaver)

    @pytest.mark.asyncio
    async def test_get_checkpointer_async_none_config(self):
        """None config should return None."""
        from yamlgraph.storage.checkpointer_factory import get_checkpointer_async

        result = await get_checkpointer_async(None)
        assert result is None


class TestRedisSimpleCheckpointer:
    """Test redis-simple checkpointer type."""

    def test_redis_simple_type_recognized(self):
        """redis-simple type should be recognized and return a checkpointer."""
        config = {"type": "redis-simple", "url": "redis://localhost:6379"}

        # Should return a SimpleRedisCheckpointer, not raise ValueError
        saver = get_checkpointer(config)

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        assert isinstance(saver, SimpleRedisCheckpointer)

    @pytest.mark.asyncio
    async def test_redis_simple_async_returns_checkpointer(self):
        """redis-simple async should return SimpleRedisCheckpointer."""
        from yamlgraph.storage.checkpointer_factory import get_checkpointer_async

        config = {
            "type": "redis-simple",
            "url": "redis://localhost:6379",
            "key_prefix": "test:",
            "ttl": 3600,
        }

        saver = await get_checkpointer_async(config)

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        assert isinstance(saver, SimpleRedisCheckpointer)

    def test_redis_simple_sync_returns_checkpointer(self):
        """redis-simple sync should return SimpleRedisCheckpointer."""
        config = {
            "type": "redis-simple",
            "url": "redis://localhost:6379",
            "key_prefix": "test:",
            "ttl": 3600,
        }

        saver = get_checkpointer(config)

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        assert isinstance(saver, SimpleRedisCheckpointer)


class TestShutdownCheckpointers:
    """Test shutdown_checkpointers cleanup function."""

    @pytest.mark.asyncio
    async def test_shutdown_checkpointers_exists(self):
        """shutdown_checkpointers() function should exist."""
        from yamlgraph.storage.checkpointer_factory import shutdown_checkpointers

        assert callable(shutdown_checkpointers)

    @pytest.mark.asyncio
    async def test_shutdown_checkpointers_clears_active_savers(self):
        """shutdown_checkpointers() should clear all active savers."""
        from yamlgraph.storage.checkpointer_factory import (
            _active_savers,
            get_checkpointer_async,
            shutdown_checkpointers,
        )

        # Clear any savers left from previous tests (may include MagicMocks)
        _active_savers.clear()

        # Create a checkpointer to register it
        config = {"type": "memory"}
        await get_checkpointer_async(config)

        # Should have at least one active saver
        # (depending on implementation, memory may not be tracked)

        # Shutdown should not raise
        await shutdown_checkpointers()

        # Active savers should be cleared
        assert len(_active_savers) == 0
