"""Tests for async executor - Phase 2 (003).

TDD: RED phase - write tests first.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from yamlgraph.executor_async import execute_prompt_async


class MockResponse(BaseModel):
    """Mock response model for testing."""

    summary: str
    score: int


# ==============================================================================
# execute_prompt_async tests (existing function - verify it works)
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_execute_prompt_async_returns_string():
    """execute_prompt_async returns string when no output_model."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Hello, World!"

    with (
        patch("yamlgraph.executor_async.create_llm", return_value=mock_llm),
        patch(
            "yamlgraph.executor_async.invoke_async", new_callable=AsyncMock
        ) as mock_invoke,
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
    ):
        mock_load.return_value = {
            "system": "You are helpful.",
            "user": "Say hello to {name}",
        }
        mock_invoke.return_value = "Hello, World!"

        result = await execute_prompt_async(
            "greet",
            variables={"name": "World"},
        )

        assert result == "Hello, World!"
        mock_invoke.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_execute_prompt_async_with_output_model():
    """execute_prompt_async returns parsed model when output_model provided."""
    mock_llm = MagicMock()
    expected = MockResponse(summary="Test", score=42)

    with (
        patch("yamlgraph.executor_async.create_llm", return_value=mock_llm),
        patch(
            "yamlgraph.executor_async.invoke_async", new_callable=AsyncMock
        ) as mock_invoke,
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
    ):
        mock_load.return_value = {
            "system": "Analyze this.",
            "user": "Input: {text}",
        }
        mock_invoke.return_value = expected

        result = await execute_prompt_async(
            "analyze",
            variables={"text": "test input"},
            output_model=MockResponse,
        )

        assert isinstance(result, MockResponse)
        assert result.summary == "Test"
        assert result.score == 42


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_execute_prompt_async_uses_provider_from_yaml():
    """execute_prompt_async extracts provider from YAML metadata."""
    mock_llm = MagicMock()

    with (
        patch(
            "yamlgraph.executor_async.create_llm", return_value=mock_llm
        ) as mock_create,
        patch(
            "yamlgraph.executor_async.invoke_async", new_callable=AsyncMock
        ) as mock_invoke,
        patch("yamlgraph.executor_base.load_prompt") as mock_load,
    ):
        mock_load.return_value = {
            "system": "Hello",
            "user": "{input}",
            "provider": "openai",  # Provider in YAML
        }
        mock_invoke.return_value = "response"

        await execute_prompt_async("test", variables={"input": "x"})

        # Should use provider from YAML
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("provider") == "openai"


# ==============================================================================
# run_graph_async tests (new function)
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_run_graph_async_executes_graph():
    """run_graph_async invokes graph asynchronously."""
    from yamlgraph.executor_async import run_graph_async

    # Mock compiled graph
    mock_app = AsyncMock()
    mock_app.ainvoke.return_value = {"output": "result", "current_step": "done"}

    result = await run_graph_async(
        mock_app,
        initial_state={"input": "test"},
        config={"configurable": {"thread_id": "t1"}},
    )

    assert result["output"] == "result"
    mock_app.ainvoke.assert_called_once_with(
        {"input": "test"},
        {"configurable": {"thread_id": "t1"}},
    )


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_run_graph_async_with_checkpointer():
    """run_graph_async works with checkpointer in config."""
    from yamlgraph.executor_async import run_graph_async

    mock_app = AsyncMock()
    mock_app.ainvoke.return_value = {"result": "ok"}

    result = await run_graph_async(
        mock_app,
        initial_state={"query": "hello"},
        config={"configurable": {"thread_id": "test-thread"}},
    )

    assert result["result"] == "ok"


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_run_graph_async_handles_interrupt():
    """run_graph_async returns interrupt payload when graph pauses."""
    from yamlgraph.executor_async import run_graph_async

    mock_app = AsyncMock()
    # Simulate interrupt response
    interrupt_value = MagicMock()
    interrupt_value.value = {"question": "What is your name?"}
    mock_app.ainvoke.return_value = {"__interrupt__": (interrupt_value,)}

    result = await run_graph_async(
        mock_app,
        initial_state={},
        config={"configurable": {"thread_id": "t1"}},
    )

    assert "__interrupt__" in result
    assert result["__interrupt__"][0].value == {"question": "What is your name?"}


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_run_graph_async_resume_with_command():
    """run_graph_async can resume with Command."""
    from langgraph.types import Command

    from yamlgraph.executor_async import run_graph_async

    mock_app = AsyncMock()
    mock_app.ainvoke.return_value = {"user_name": "Alice", "greeting": "Hello Alice!"}

    result = await run_graph_async(
        mock_app,
        initial_state=Command(resume="Alice"),
        config={"configurable": {"thread_id": "t1"}},
    )

    assert result["user_name"] == "Alice"
    mock_app.ainvoke.assert_called_once()


# ==============================================================================
# compile_graph_async tests (new function)
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_compile_graph_async_with_memory_checkpointer():
    """compile_graph_async compiles graph with memory checkpointer."""
    from yamlgraph.executor_async import compile_graph_async

    # Use minimal test graph - now uses get_checkpointer_async
    with patch(
        "yamlgraph.storage.checkpointer_factory.get_checkpointer_async"
    ) as mock_cp:
        from langgraph.checkpoint.memory import MemorySaver

        mock_cp.return_value = MemorySaver()

        config = MagicMock()
        config.checkpointer = {"type": "memory"}

        mock_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_graph.compile.return_value = mock_compiled

        result = await compile_graph_async(mock_graph, config)

        mock_graph.compile.assert_called_once()
        assert result == mock_compiled


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_compile_graph_async_uses_async_factory():
    """compile_graph_async uses get_checkpointer_async."""
    from yamlgraph.executor_async import compile_graph_async

    with patch(
        "yamlgraph.storage.checkpointer_factory.get_checkpointer_async"
    ) as mock_cp:
        mock_cp.return_value = MagicMock()

        mock_graph = MagicMock()
        mock_graph.compile.return_value = MagicMock()

        config = MagicMock()
        config.checkpointer = {"type": "redis", "url": "redis://localhost"}

        await compile_graph_async(mock_graph, config)

        mock_cp.assert_called_once_with(config.checkpointer)


# ==============================================================================
# load_and_compile_async tests (convenience function)
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_load_and_compile_async_returns_compiled_graph():
    """load_and_compile_async loads YAML and returns compiled graph."""
    from yamlgraph.executor_async import load_and_compile_async

    with (
        patch("yamlgraph.graph_loader.load_graph_config") as mock_load,
        patch("yamlgraph.graph_loader.compile_graph") as mock_compile,
        patch("yamlgraph.storage.checkpointer_factory.get_checkpointer") as mock_cp,
    ):
        mock_config = MagicMock()
        mock_config.name = "test-graph"
        mock_config.version = "1.0"
        mock_config.checkpointer = {"type": "memory"}
        mock_load.return_value = mock_config

        mock_state_graph = MagicMock()
        mock_compiled = MagicMock()
        mock_state_graph.compile.return_value = mock_compiled
        mock_compile.return_value = mock_state_graph

        mock_cp.return_value = None

        result = await load_and_compile_async("graphs/test.yaml")

        assert result == mock_compiled
        mock_load.assert_called_once_with("graphs/test.yaml")


# ==============================================================================
# Concurrent execution tests
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_run_graphs_concurrent():
    """Multiple graphs can run concurrently."""
    from yamlgraph.executor_async import run_graph_async

    mock_app1 = AsyncMock()
    mock_app1.ainvoke.return_value = {"result": "first"}

    mock_app2 = AsyncMock()
    mock_app2.ainvoke.return_value = {"result": "second"}

    results = await asyncio.gather(
        run_graph_async(mock_app1, {}, {"configurable": {"thread_id": "t1"}}),
        run_graph_async(mock_app2, {}, {"configurable": {"thread_id": "t2"}}),
    )

    assert results[0]["result"] == "first"
    assert results[1]["result"] == "second"


# ==============================================================================
# Error handling tests
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_run_graph_async_propagates_errors():
    """run_graph_async propagates exceptions from graph execution."""
    from yamlgraph.executor_async import run_graph_async

    mock_app = AsyncMock()
    mock_app.ainvoke.side_effect = ValueError("Graph execution failed")

    with pytest.raises(ValueError, match="Graph execution failed"):
        await run_graph_async(
            mock_app,
            initial_state={},
            config={"configurable": {"thread_id": "t1"}},
        )


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-015")
async def test_compile_graph_async_without_checkpointer():
    """compile_graph_async works without checkpointer config."""
    from yamlgraph.executor_async import compile_graph_async

    mock_graph = MagicMock()
    mock_compiled = MagicMock()
    mock_graph.compile.return_value = mock_compiled

    config = MagicMock()
    config.checkpointer = None

    with patch(
        "yamlgraph.storage.checkpointer_factory.get_checkpointer_async",
        return_value=None,
    ):
        result = await compile_graph_async(mock_graph, config)

    mock_graph.compile.assert_called_once_with(checkpointer=None)
    assert result == mock_compiled
