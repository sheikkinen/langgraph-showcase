"""Integration tests for FR-028: Multi-Turn Streaming.

Tests the full flow of multi-turn conversations with:
- New session creation with checkpoint
- Resume from interrupt with Command
- Guard classification as separate call
- Checkpoint persistence

Uses run_graph_streaming_native() for token streaming and
run_graph_async() for non-streaming multi-turn operations.
"""

import pytest
from langgraph.types import Command


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-049")
async def test_multi_turn_resume_with_command():
    """Multi-turn resume works with Command and checkpointer."""
    from yamlgraph.executor_async import load_and_compile_async, run_graph_async

    graph_path = "examples/demos/multi-turn/graph.yaml"
    thread_id = "test-session-resume-cmd"
    config = {"configurable": {"thread_id": thread_id}}

    app = await load_and_compile_async(graph_path)

    # Turn 1: start session, hit interrupt
    result1 = await run_graph_async(app, {"user_message": ""}, config)
    assert "__interrupt__" in result1, "Turn 1 should interrupt"

    # Turn 2: resume with Command → runs respond → hits interrupt again
    result2 = await run_graph_async(app, Command(resume="tell me a joke"), config)

    # Should have response from LLM
    assert result2.get("response"), f"Turn 2 should have response, got: {result2}"
    # Should hit interrupt again for next turn
    assert "__interrupt__" in result2, "Turn 2 should interrupt for next turn"


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-049")
async def test_guard_classification_separate_call():
    """Guard classification works as separate graph call."""
    from yamlgraph.graph_loader import load_and_compile

    guard_path = "examples/demos/multi-turn/guard.yaml"
    graph = load_and_compile(guard_path)
    compiled = graph.compile()

    # Test "stop" intent
    result = await compiled.ainvoke({"user_message": "stop"})
    intent = result.get("intent", "").lower().strip()
    assert "stop" in intent, f"'stop' should classify as stop, got: {intent}"

    # Test "continue" intent
    result = await compiled.ainvoke({"user_message": "tell me a joke"})
    intent = result.get("intent", "").lower().strip()
    assert (
        "continue" in intent
    ), f"Normal message should classify as continue, got: {intent}"


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-049")
async def test_checkpointer_persists_across_turns():
    """State persists across turns via checkpointer."""
    from yamlgraph.executor_async import load_and_compile_async, run_graph_async

    graph_path = "examples/demos/multi-turn/graph.yaml"
    thread_id = "test-persistence-turns"
    config = {"configurable": {"thread_id": thread_id}}

    app = await load_and_compile_async(graph_path)

    # Turn 1: hits interrupt
    result1 = await run_graph_async(app, {"user_message": ""}, config)
    assert "__interrupt__" in result1

    # Turn 2: resume with message
    result2 = await run_graph_async(app, Command(resume="my name is Alice"), config)
    assert result2.get("response"), "Turn 2 should have response"
    response2 = result2["response"]

    # Turn 3: resume again - should have context from previous turns
    result3 = await run_graph_async(app, Command(resume="what did I just say?"), config)
    assert result3.get("response"), "Turn 3 should have response"

    # Both turns should have produced LLM responses (proving checkpointing worked)
    assert len(response2) > 0, "Turn 2 response should not be empty"
    assert len(result3["response"]) > 0, "Turn 3 response should not be empty"


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-049")
async def test_streaming_signature_accepts_command():
    """run_graph_streaming_native signature accepts Command type."""
    import inspect

    from yamlgraph.executor_async import run_graph_streaming_native

    sig = inspect.signature(run_graph_streaming_native)
    annotation = str(sig.parameters["initial_state"].annotation)
    assert "Command" in annotation, f"Should accept Command, got: {annotation}"


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-049")
async def test_streaming_signature_accepts_config():
    """run_graph_streaming_native signature accepts config parameter."""
    import inspect

    from yamlgraph.executor_async import run_graph_streaming_native

    sig = inspect.signature(run_graph_streaming_native)
    params = list(sig.parameters.keys())
    assert "config" in params, f"Should have config parameter, got: {params}"
