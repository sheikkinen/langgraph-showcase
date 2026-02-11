"""Token usage tracking callback (FR-027 P2-8, REQ-YG-064).

Provides a LangChain callback handler that accumulates token usage
across all LLM invocations in a graph run.  Injected into the graph
config alongside the LangSmith tracer — same ``config["callbacks"]``
pattern established by :mod:`yamlgraph.utils.tracing`.

Usage::

    from yamlgraph.utils.token_tracker import create_token_tracker

    tracker = create_token_tracker()
    config.setdefault("callbacks", []).append(tracker)
    result = app.invoke(state, config=config)

    if tracker.total_calls > 0:
        print(tracker.summary())
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger(__name__)


class TokenUsageCallbackHandler(BaseCallbackHandler):
    """Accumulates token usage across all LLM calls in a graph run.

    Works transparently with ``graph.invoke()`` via LangGraph's
    ``contextvars``-based callback propagation — no modification to
    node functions required.

    Reads ``usage_metadata`` from ``AIMessage`` (the LangChain-normalised
    path), which is provider-independent:
    ``{"input_tokens": N, "output_tokens": N, "total_tokens": N}``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_calls: int = 0

    # -- LangChain callback ---------------------------------------------------

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:  # noqa: ARG002
        """Called once per ``llm.invoke()`` / ``llm.ainvoke()`` call.

        Extracts ``usage_metadata`` from each generation's ``AIMessage``.
        Gracefully ignores responses without usage data (e.g. local models).
        """
        self.total_calls += 1
        for gen_list in response.generations:
            for gen in gen_list:
                message = getattr(gen, "message", None)
                if message is None:
                    continue
                usage = getattr(message, "usage_metadata", None)
                if usage is None:
                    continue
                self.total_input_tokens += usage.get("input_tokens", 0)
                self.total_output_tokens += usage.get("output_tokens", 0)

    # -- Public API ------------------------------------------------------------

    def summary(self) -> dict[str, int]:
        """Return accumulated token usage as a plain dict.

        Returns:
            Dict with ``total_input_tokens``, ``total_output_tokens``,
            ``total_tokens`` (sum), and ``total_calls``.
        """
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_calls": self.total_calls,
        }


def create_token_tracker() -> TokenUsageCallbackHandler:
    """Factory — mirrors :func:`yamlgraph.utils.tracing.create_tracer`.

    Returns:
        A fresh :class:`TokenUsageCallbackHandler` instance.
    """
    return TokenUsageCallbackHandler()
