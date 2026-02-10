"""Tests for streaming support - Phase 3 (004).

TDD: RED phase - write tests first.
"""

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# execute_prompt_streaming tests
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-009")
async def test_execute_prompt_streaming_yields_tokens():
    """execute_prompt_streaming yields tokens from LLM stream."""
    from yamlgraph.executor_async import execute_prompt_streaming

    # Mock LLM with astream method
    mock_chunk1 = MagicMock()
    mock_chunk1.content = "Hello"
    mock_chunk2 = MagicMock()
    mock_chunk2.content = " World"
    mock_chunk3 = MagicMock()
    mock_chunk3.content = "!"

    async def mock_astream(*args, **kwargs):
        for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
            yield chunk

    mock_llm = MagicMock()
    mock_llm.astream = mock_astream

    with (
        patch("yamlgraph.executor_async.create_llm", return_value=mock_llm),
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
    ):
        mock_load.return_value = {
            "system": "You are helpful.",
            "user": "Say hello",
        }

        tokens = []
        async for token in execute_prompt_streaming("greet", variables={}):
            tokens.append(token)

        assert tokens == ["Hello", " World", "!"]


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-009")
async def test_execute_prompt_streaming_with_variables():
    """execute_prompt_streaming formats template with variables."""
    from yamlgraph.executor_async import execute_prompt_streaming

    mock_chunk = MagicMock()
    mock_chunk.content = "Hi Alice!"

    async def mock_astream(*args, **kwargs):
        yield mock_chunk

    mock_llm = MagicMock()
    mock_llm.astream = mock_astream

    with (
        patch("yamlgraph.executor_async.create_llm", return_value=mock_llm),
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
        patch(
            "yamlgraph.executor_base.format_prompt", return_value="Say hello to Alice"
        ),
    ):
        mock_load.return_value = {
            "system": "",
            "user": "Say hello to {name}",
        }

        tokens = []
        async for token in execute_prompt_streaming(
            "greet", variables={"name": "Alice"}
        ):
            tokens.append(token)

        assert tokens == ["Hi Alice!"]


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-009")
async def test_execute_prompt_streaming_uses_provider():
    """execute_prompt_streaming passes provider to create_llm."""
    from yamlgraph.executor_async import execute_prompt_streaming

    mock_chunk = MagicMock()
    mock_chunk.content = "test"

    async def mock_astream(*args, **kwargs):
        yield mock_chunk

    mock_llm = MagicMock()
    mock_llm.astream = mock_astream

    with (
        patch(
            "yamlgraph.executor_async.create_llm", return_value=mock_llm
        ) as mock_create,
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
    ):
        mock_load.return_value = {"system": "", "user": "test"}

        async for _ in execute_prompt_streaming(
            "test", variables={}, provider="openai"
        ):
            pass

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("provider") == "openai"


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-009")
async def test_execute_prompt_streaming_handles_empty_chunks():
    """execute_prompt_streaming skips empty chunks."""
    from yamlgraph.executor_async import execute_prompt_streaming

    mock_chunk1 = MagicMock()
    mock_chunk1.content = "Hello"
    mock_chunk2 = MagicMock()
    mock_chunk2.content = ""  # Empty
    mock_chunk3 = MagicMock()
    mock_chunk3.content = None  # None
    mock_chunk4 = MagicMock()
    mock_chunk4.content = "World"

    async def mock_astream(*args, **kwargs):
        for chunk in [mock_chunk1, mock_chunk2, mock_chunk3, mock_chunk4]:
            yield chunk

    mock_llm = MagicMock()
    mock_llm.astream = mock_astream

    with (
        patch("yamlgraph.executor_async.create_llm", return_value=mock_llm),
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
    ):
        mock_load.return_value = {"system": "", "user": "test"}

        tokens = []
        async for token in execute_prompt_streaming("test", variables={}):
            tokens.append(token)

        # Only non-empty tokens
        assert tokens == ["Hello", "World"]


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-009")
async def test_execute_prompt_streaming_propagates_errors():
    """execute_prompt_streaming propagates LLM errors."""
    from yamlgraph.executor_async import execute_prompt_streaming

    async def mock_astream(*args, **kwargs):
        yield MagicMock(content="start")
        raise ValueError("LLM error")

    mock_llm = MagicMock()
    mock_llm.astream = mock_astream

    with (
        patch("yamlgraph.executor_async.create_llm", return_value=mock_llm),
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
    ):
        mock_load.return_value = {"system": "", "user": "test"}

        tokens = []
        with pytest.raises(ValueError, match="LLM error"):
            async for token in execute_prompt_streaming("test", variables={}):
                tokens.append(token)

        # Should have received first token before error
        assert tokens == ["start"]


# ==============================================================================
# Streaming with output collection
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-009")
async def test_execute_prompt_streaming_collect():
    """execute_prompt_streaming can collect all tokens into string."""
    from yamlgraph.executor_async import execute_prompt_streaming

    mock_chunks = [MagicMock(content=c) for c in ["The ", "quick ", "brown ", "fox"]]

    async def mock_astream(*args, **kwargs):
        for chunk in mock_chunks:
            yield chunk

    mock_llm = MagicMock()
    mock_llm.astream = mock_astream

    with (
        patch("yamlgraph.executor_async.create_llm", return_value=mock_llm),
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
    ):
        mock_load.return_value = {"system": "", "user": "test"}

        # Collect all tokens
        result = "".join(
            [token async for token in execute_prompt_streaming("test", {})]
        )

        assert result == "The quick brown fox"


# ==============================================================================
# Streaming node factory tests
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-009")
async def test_create_streaming_node_yields_tokens():
    """create_streaming_node creates node that yields tokens."""
    from yamlgraph.node_factory import create_streaming_node

    mock_chunks = [MagicMock(content=c) for c in ["Hello", " ", "World"]]

    async def mock_streaming(*args, **kwargs):
        for chunk in mock_chunks:
            yield chunk.content

    with patch("yamlgraph.executor_async.execute_prompt_streaming", mock_streaming):
        node_config = {
            "prompt": "greet",
            "state_key": "response",
        }
        streaming_node = create_streaming_node("generate", node_config)

        state = {"input": "test"}
        tokens = []
        async for token in streaming_node(state):
            tokens.append(token)

        assert tokens == ["Hello", " ", "World"]


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-009")
async def test_streaming_node_with_callback():
    """Streaming node can use callback for each token."""
    from yamlgraph.node_factory import create_streaming_node

    async def mock_streaming(*args, **kwargs):
        for token in ["A", "B", "C"]:
            yield token

    collected = []

    def token_callback(token: str):
        collected.append(token)

    with patch("yamlgraph.executor_async.execute_prompt_streaming", mock_streaming):
        node_config = {
            "prompt": "test",
            "state_key": "output",
            "on_token": token_callback,
        }
        streaming_node = create_streaming_node("stream_node", node_config)

        # Consume the generator
        async for _ in streaming_node({}):
            pass

        assert collected == ["A", "B", "C"]


# ==============================================================================
# YAML config tests
# ==============================================================================


@pytest.mark.req("REQ-YG-009")
def test_node_config_stream_true_creates_streaming_node():
    """Node with stream: true creates streaming node."""
    from yamlgraph.node_factory import create_node_function

    node_config = {
        "prompt": "greet",
        "state_key": "response",
        "stream": True,
    }

    with patch("yamlgraph.node_factory.streaming.create_streaming_node") as mock_create:
        mock_create.return_value = MagicMock()

        # This should detect stream: true and use create_streaming_node
        _result = create_node_function("generate", node_config, defaults={})

        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[0] == ("generate", node_config)
        # Verify prompt resolution params are passed
        assert "graph_path" in call_args[1]
        assert "prompts_dir" in call_args[1]
        assert "prompts_relative" in call_args[1]


@pytest.mark.req("REQ-YG-009")
def test_node_config_stream_false_creates_regular_node():
    """Node with stream: false creates regular node."""
    from yamlgraph.node_factory import create_node_function

    node_config = {
        "prompt": "greet",
        "state_key": "response",
        "stream": False,
    }

    with (
        patch(
            "yamlgraph.node_factory.streaming.create_streaming_node"
        ) as mock_streaming,
        patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
    ):
        mock_execute.return_value = "result"

        _result = create_node_function("generate", node_config, defaults={})

        # Should NOT call create_streaming_node
        mock_streaming.assert_not_called()
