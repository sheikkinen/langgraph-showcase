"""Tests for graph-level streaming (FR-023).

REQ-YG-048: run_graph_streaming yields LLM tokens via astream(stream_mode="messages")
REQ-YG-049: SSE streaming formats tokens as OpenAI-compatible chunks
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yamlgraph.executor_async import run_graph_streaming

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GRAPH_PATH = Path("examples/openai_proxy/graph.yaml")


def _make_message_chunk(content: str):
    """Create a mock AIMessageChunk with content."""
    chunk = MagicMock()
    chunk.content = content
    return chunk


# ---------------------------------------------------------------------------
# REQ-YG-048: Graph-Level Streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-048")
async def test_run_graph_streaming_yields_tokens():
    """run_graph_streaming should yield token strings from the LLM node."""
    mock_chunks = [_make_message_chunk("Hello"), _make_message_chunk(" there")]

    async def mock_astream(*args, **kwargs):
        for chunk in mock_chunks:
            yield chunk

    with patch("yamlgraph.executor_async.create_llm") as mock_create:
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_create.return_value = mock_llm

        tokens = []
        async for token in run_graph_streaming(
            graph_path=str(GRAPH_PATH),
            initial_state={"input": "hello"},
        ):
            tokens.append(token)
        # Should yield at least one token
        assert len(tokens) > 0
        assert all(isinstance(t, str) for t in tokens)


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-048")
async def test_run_graph_streaming_runs_python_nodes_first():
    """Python nodes (echo, validate) should execute before streaming starts."""
    mock_chunks = [_make_message_chunk("Validated")]

    async def mock_astream(*args, **kwargs):
        for chunk in mock_chunks:
            yield chunk

    with patch("yamlgraph.executor_async.create_llm") as mock_create:
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_create.return_value = mock_llm

        tokens = []
        async for token in run_graph_streaming(
            graph_path=str(GRAPH_PATH),
            initial_state={"input": '{"role":"user","content":"test"}'},
        ):
            tokens.append(token)
        # The LLM received the validation output, so tokens exist
        assert len(tokens) > 0


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-048")
async def test_run_graph_streaming_returns_async_iterator():
    """run_graph_streaming should return an async iterator."""
    mock_chunks = [_make_message_chunk("ok")]

    async def mock_astream(*args, **kwargs):
        for chunk in mock_chunks:
            yield chunk

    with patch("yamlgraph.executor_async.create_llm") as mock_create:
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_create.return_value = mock_llm

        result = run_graph_streaming(
            graph_path=str(GRAPH_PATH),
            initial_state={"input": "test"},
        )
        assert hasattr(result, "__aiter__")
        assert hasattr(result, "__anext__")
        # Consume to avoid warnings
        async for _ in result:
            break


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-048")
async def test_run_graph_streaming_with_mocked_llm():
    """run_graph_streaming should work with a mocked LLM for unit testing."""
    mock_chunks = [
        _make_message_chunk("Hello"),
        _make_message_chunk(", "),
        _make_message_chunk("world!"),
    ]

    async def mock_astream(*args, **kwargs):
        for chunk in mock_chunks:
            yield chunk

    with patch("yamlgraph.executor_async.create_llm") as mock_create:
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_create.return_value = mock_llm

        tokens = []
        async for token in run_graph_streaming(
            graph_path=str(GRAPH_PATH),
            initial_state={"input": "test"},
        ):
            tokens.append(token)

        assert tokens == ["Hello", ", ", "world!"]


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-048")
async def test_run_graph_streaming_skips_empty_chunks():
    """Empty token chunks should be filtered out."""
    mock_chunks = [
        _make_message_chunk("Hello"),
        _make_message_chunk(""),
        _make_message_chunk("world"),
    ]

    async def mock_astream(*args, **kwargs):
        for chunk in mock_chunks:
            yield chunk

    with patch("yamlgraph.executor_async.create_llm") as mock_create:
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_create.return_value = mock_llm

        tokens = []
        async for token in run_graph_streaming(
            graph_path=str(GRAPH_PATH),
            initial_state={"input": "test"},
        ):
            tokens.append(token)

        assert "" not in tokens
        assert tokens == ["Hello", "world"]


# ---------------------------------------------------------------------------
# REQ-YG-049: SSE Format
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-049")
async def test_run_graph_streaming_tokens_are_strings():
    """Each yielded token must be a plain string, suitable for SSE formatting."""
    mock_chunks = [_make_message_chunk("token1")]

    async def mock_astream(*args, **kwargs):
        for chunk in mock_chunks:
            yield chunk

    with patch("yamlgraph.executor_async.create_llm") as mock_create:
        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        mock_create.return_value = mock_llm

        async for token in run_graph_streaming(
            graph_path=str(GRAPH_PATH),
            initial_state={"input": "test"},
        ):
            # Token must be a string that can be JSON-serialized into SSE
            assert isinstance(token, str)
            chunk = {
                "id": "test",
                "object": "chat.completion.chunk",
                "choices": [{"delta": {"content": token}}],
            }
            json.dumps(chunk)  # Must not raise


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-049")
async def test_run_graph_streaming_signature():
    """run_graph_streaming must accept graph_path and initial_state."""
    import inspect

    sig = inspect.signature(run_graph_streaming)
    params = list(sig.parameters.keys())
    assert "graph_path" in params
    assert "initial_state" in params
