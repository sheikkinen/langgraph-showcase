"""Checkpointer factory for YAML-configured persistence.

Creates checkpointer instances from YAML configuration with support for:
- Multiple backends (memory, sqlite, redis)
- Environment variable expansion for secrets
- Sync and async modes for Redis
"""

import os
import re
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver


def expand_env_vars(value: Any) -> Any:
    """Expand ${VAR} patterns in string.

    Args:
        value: Value to expand. Non-strings pass through unchanged.

    Returns:
        String with ${VAR} patterns replaced by environment values.
        Missing vars keep original ${VAR} pattern.
    """
    if not isinstance(value, str):
        return value

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))

    return re.sub(r"\$\{([^}]+)\}", replacer, value)


def get_checkpointer(
    config: dict | None,
) -> BaseCheckpointSaver | None:
    """Create checkpointer from config.

    Args:
        config: Checkpointer configuration dict with keys:
            - type: "memory" | "sqlite" | "redis" | "redis-simple" (default: "memory")
            - url: Redis connection URL (for redis/redis-simple types)
            - path: SQLite file path (for sqlite type)
            - ttl: TTL in minutes (for redis types, default: 60)

    Returns:
        Configured checkpointer or None if config is None

    Raises:
        ValueError: If unknown checkpointer type
        ImportError: If redis type used without yamlgraph[redis] installed

    Note:
        For async usage (FastAPI), use get_checkpointer_async() instead.
    """
    if not config:
        return None

    cp_type = config.get("type", "memory")

    if cp_type == "redis":
        url = expand_env_vars(config.get("url", ""))
        ttl = config.get("ttl", 60)

        try:
            from langgraph.checkpoint.redis import RedisSaver

            saver = RedisSaver(
                redis_url=url,
                ttl={"default_ttl": ttl},
            )
            saver.setup()

            return saver
        except ImportError as e:
            raise ImportError(
                "Install redis support: pip install yamlgraph[redis]"
            ) from e

    elif cp_type == "sqlite":
        path = expand_env_vars(config.get("path", ":memory:"))
        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver

        conn = sqlite3.connect(path, check_same_thread=False)
        return SqliteSaver(conn)

    elif cp_type == "redis-simple":
        url = expand_env_vars(config.get("url", ""))
        if not url or url.startswith("${"):
            # URL not set or env var not expanded
            import logging

            logging.getLogger(__name__).warning(
                "redis-simple URL not set, falling back to MemorySaver"
            )
            from langgraph.checkpoint.memory import MemorySaver

            return MemorySaver()

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        return SimpleRedisCheckpointer(
            redis_url=url,
            key_prefix=config.get("key_prefix", "lg:"),
            ttl=config.get("ttl"),
            max_connections=config.get("max_connections", 10),
        )

    elif cp_type == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()

    raise ValueError(f"Unknown checkpointer type: {cp_type}")


# =============================================================================
# Async checkpointer factory
# =============================================================================

# Track active savers for cleanup
_active_savers: list = []


async def get_checkpointer_async(
    config: dict | None,
) -> BaseCheckpointSaver | None:
    """Create async-compatible checkpointer from config.

    For Redis, uses direct instantiation with asetup().
    For redis-simple, returns SimpleRedisCheckpointer.
    For memory/sqlite, delegates to sync get_checkpointer().

    Args:
        config: Checkpointer configuration dict with keys:
            - type: "memory" | "sqlite" | "redis" | "redis-simple"
            - url: Redis connection URL (for redis/redis-simple types)
            - path: SQLite file path (for sqlite type)
            - ttl: TTL in seconds (for redis types)
            - key_prefix: Key prefix (for redis-simple)

    Returns:
        Configured checkpointer or None if config is None
    """
    if not config:
        return None

    cp_type = config.get("type", "memory")

    if cp_type == "redis":
        url = expand_env_vars(config.get("url", ""))
        ttl = config.get("ttl", 60)

        # Check if URL is set
        if not url or url.startswith("${"):
            import logging

            logging.getLogger(__name__).warning(
                "REDIS_URL not set, falling back to MemorySaver"
            )
            from langgraph.checkpoint.memory import MemorySaver

            return MemorySaver()

        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver

            saver = AsyncRedisSaver(
                redis_url=url,
                ttl={"default_ttl": ttl},
            )
            await saver.asetup()
            _active_savers.append(saver)
            return saver
        except ImportError as e:
            raise ImportError(
                "Install redis support: pip install yamlgraph[redis]"
            ) from e

    elif cp_type == "redis-simple":
        url = expand_env_vars(config.get("url", ""))
        if not url or url.startswith("${"):
            import logging

            logging.getLogger(__name__).warning(
                "redis-simple URL not set, falling back to MemorySaver"
            )
            from langgraph.checkpoint.memory import MemorySaver

            return MemorySaver()

        from yamlgraph.storage.simple_redis import SimpleRedisCheckpointer

        saver = SimpleRedisCheckpointer(
            redis_url=url,
            key_prefix=config.get("key_prefix", "lg:"),
            ttl=config.get("ttl"),
            max_connections=config.get("max_connections", 10),
        )
        _active_savers.append(saver)
        return saver

    # memory/sqlite don't need async init
    return get_checkpointer(config)


async def shutdown_checkpointers() -> None:
    """Close all active Redis connections.

    Call this on application shutdown for graceful cleanup.

    Example with FastAPI:
        from contextlib import asynccontextmanager
        from yamlgraph.storage.checkpointer_factory import shutdown_checkpointers

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            await shutdown_checkpointers()

        app = FastAPI(lifespan=lifespan)
    """
    global _active_savers
    for saver in _active_savers:
        if hasattr(saver, "aclose"):
            await saver.aclose()
        elif hasattr(saver, "__aexit__"):
            await saver.__aexit__(None, None, None)
    _active_savers.clear()
