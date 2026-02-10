"""LangSmith tracing utilities (FR-022).

Provides safe, reusable helpers for LangSmith trace URL retrieval
and public trace sharing. Used by CLI and API consumers.

Auto-detects tracing via the LangSmith SDK, which accepts both current
(LANGCHAIN_TRACING_V2, LANGSMITH_API_KEY) and legacy (LANGCHAIN_TRACING,
LANGCHAIN_API_KEY) environment variable names. All functions are fail-safe
— they return None on error and never raise exceptions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.tracers import LangChainTracer as LangChainTracerType

logger = logging.getLogger(__name__)


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is configured.

    Delegates to the LangSmith SDK's own detection, which accepts both
    current and legacy env var names:
    - LANGCHAIN_TRACING_V2 / LANGCHAIN_TRACING
    - LANGSMITH_API_KEY / LANGCHAIN_API_KEY
    """
    try:
        from langsmith.utils import tracing_is_enabled

        return tracing_is_enabled()
    except Exception:
        return False


def create_tracer(
    project_name: str | None = None,
) -> LangChainTracerType | None:
    """Create a LangChainTracer if tracing is enabled.

    Args:
        project_name: Optional LangSmith project name.
            Defaults to LANGCHAIN_PROJECT env var.

    Returns:
        LangChainTracer instance or None if tracing is not enabled.
    """
    if not is_tracing_enabled():
        return None

    from langchain_core.tracers import LangChainTracer

    return LangChainTracer(project_name=project_name)


def get_trace_url(tracer: LangChainTracerType | None) -> str | None:
    """Get the authenticated trace URL from a tracer.

    Args:
        tracer: LangChainTracer instance (or None).

    Returns:
        Trace URL string or None if unavailable.
    """
    if tracer is None:
        return None
    try:
        return tracer.get_run_url()
    except Exception:
        logger.warning("Failed to retrieve trace URL", exc_info=True)
        return None


def share_trace(tracer: LangChainTracerType | None) -> str | None:
    """Share a trace publicly and return the public URL.

    Calls LangSmith's share_run API to make the trace publicly
    accessible without authentication.

    Args:
        tracer: LangChainTracer instance (or None).

    Returns:
        Public trace URL string or None if unavailable.
    """
    if tracer is None:
        return None
    try:
        if tracer.latest_run is None:
            return None
        return tracer.client.share_run(tracer.latest_run.id)
    except Exception:
        logger.warning("Failed to share trace", exc_info=True)
        return None


def inject_tracer_config(
    config: dict[str, Any], tracer: LangChainTracerType | None
) -> dict[str, Any]:
    """Inject a tracer callback into a LangGraph config dict.

    Adds the tracer to the ``callbacks`` list without overwriting
    existing config keys.

    Args:
        config: Existing config dict (may be empty).
        tracer: LangChainTracer to inject (or None to no-op).

    Returns:
        The config dict (mutated in-place and returned for convenience).
    """
    if tracer is None:
        return config
    callbacks = config.setdefault("callbacks", [])
    callbacks.append(tracer)
    return config
