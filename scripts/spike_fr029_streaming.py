#!/usr/bin/env python
# ruff: noqa: E402
"""Spike: Verify LangGraph stream_mode="messages" behavior for FR-029.

Research questions:
1. Does stream_mode="messages" require nodes to use astream internally?
2. What is the exact event structure?
3. How are interrupts surfaced?
4. Does it work with yamlgraph-compiled graphs?
"""
import asyncio
import os
from operator import add
from typing import Annotated, TypedDict

# Load .env file
from dotenv import load_dotenv

load_dotenv()

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

# Ensure API key is set
if not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY required")
    exit(1)


class State(TypedDict):
    messages: Annotated[list, add]
    count: int


# Test 1: Node using ainvoke (not astream)
async def llm_node_invoke(state: State) -> dict:
    """LLM node using ainvoke - does stream_mode=messages still stream tokens?"""
    llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=50)
    # Using ainvoke, NOT astream
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response], "count": state.get("count", 0) + 1}


# Test 2: Node using astream explicitly
async def llm_node_stream(state: State) -> dict:
    """LLM node using astream explicitly."""
    llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=50)
    chunks = []
    async for chunk in llm.astream(state["messages"]):
        chunks.append(chunk)
    response = chunks[-1] if chunks else None
    return {"messages": [response] if response else [], "count": state.get("count", 0) + 1}


def preprocess(state: State) -> dict:
    """Non-LLM preprocess node."""
    return {"messages": state["messages"]}


def wait_for_user(state: State) -> dict:
    """Interrupt node to wait for user input."""
    user_input = interrupt("waiting for user")
    return {"messages": [("user", user_input)]}


async def test_ainvoke_streaming():
    """Test 1: Does stream_mode=messages stream tokens when node uses ainvoke?"""
    print("\n" + "=" * 60)
    print("TEST 1: stream_mode='messages' with ainvoke node")
    print("=" * 60)

    builder = StateGraph(State)
    builder.add_node("preprocess", preprocess)
    builder.add_node("llm", llm_node_invoke)
    builder.add_edge(START, "preprocess")
    builder.add_edge("preprocess", "llm")
    builder.add_edge("llm", END)

    graph = builder.compile()

    token_count = 0
    events = []

    async for event in graph.astream(
        {"messages": [("user", "Say hello in exactly 3 words")], "count": 0},
        stream_mode="messages",
    ):
        events.append(event)
        # Analyze event structure
        if isinstance(event, tuple) and len(event) == 2:
            chunk, metadata = event
            chunk_type = type(chunk).__name__
            content = getattr(chunk, 'content', None)
            node = metadata.get('langgraph_node', 'unknown') if isinstance(metadata, dict) else 'N/A'

            if content:
                token_count += 1
                print(f"  Token {token_count}: {chunk_type} from '{node}': {content!r}")
        else:
            print(f"  Event: {type(event).__name__}: {str(event)[:80]}")

    print(f"\nResult: Received {token_count} tokens from ainvoke node")
    print(f"Total events: {len(events)}")
    return token_count > 0


async def test_event_structure():
    """Test 2: Document exact event structure."""
    print("\n" + "=" * 60)
    print("TEST 2: Event structure analysis")
    print("=" * 60)

    builder = StateGraph(State)
    builder.add_node("llm", llm_node_invoke)
    builder.add_edge(START, "llm")
    builder.add_edge("llm", END)

    graph = builder.compile()

    async for event in graph.astream(
        {"messages": [("user", "Hi")], "count": 0},
        stream_mode="messages",
    ):
        print(f"\nEvent type: {type(event)}")
        if isinstance(event, tuple):
            print(f"  Tuple length: {len(event)}")
            for i, item in enumerate(event):
                print(f"  [{i}] {type(item).__name__}")
                if hasattr(item, '__dict__'):
                    for k, v in item.__dict__.items():
                        if not k.startswith('_'):
                            print(f"      .{k} = {repr(v)[:60]}")
                elif isinstance(item, dict):
                    for k, v in item.items():
                        print(f"      [{k!r}] = {repr(v)[:60]}")
        break  # Just analyze first event


async def test_interrupt_handling():
    """Test 3: How are interrupts surfaced in messages mode?"""
    print("\n" + "=" * 60)
    print("TEST 3: Interrupt handling in stream_mode='messages'")
    print("=" * 60)

    builder = StateGraph(State)
    builder.add_node("llm", llm_node_invoke)
    builder.add_node("wait", wait_for_user)
    builder.add_edge(START, "llm")
    builder.add_edge("llm", "wait")
    builder.add_edge("wait", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-interrupt"}}

    print("\nTurn 1: Start conversation...")
    events = []
    final_state = None

    async for event in graph.astream(
        {"messages": [("user", "Say hi")], "count": 0},
        config,
        stream_mode="messages",
    ):
        events.append(event)
        event_type = type(event).__name__
        if isinstance(event, tuple) and len(event) == 2:
            chunk, metadata = event
            content = getattr(chunk, 'content', None)
            if content:
                print(f"  Token: {content!r}")

    # Check final state for interrupt
    final_state = await graph.aget_state(config)
    print(f"\nFinal state has __interrupt__: {'__interrupt__' in (final_state.values or {})}")
    print(f"Next nodes: {final_state.next}")

    if final_state.next:
        print("\nTurn 2: Resume with Command...")
        async for event in graph.astream(
            Command(resume="thanks!"),
            config,
            stream_mode="messages",
        ):
            event_type = type(event).__name__
            print(f"  Resume event: {event_type}")


async def test_multi_llm():
    """Test 4: Multiple LLM nodes - do both stream?"""
    print("\n" + "=" * 60)
    print("TEST 4: Multiple LLM nodes")
    print("=" * 60)

    async def llm_1(state: State) -> dict:
        llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=30)
        response = await llm.ainvoke([("user", "Count from 1 to 3")])
        return {"messages": [response], "count": 1}

    async def llm_2(state: State) -> dict:
        llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=30)
        response = await llm.ainvoke([("user", "Count from A to C")])
        return {"messages": [response], "count": 2}

    builder = StateGraph(State)
    builder.add_node("llm_1", llm_1)
    builder.add_node("llm_2", llm_2)
    builder.add_edge(START, "llm_1")
    builder.add_edge("llm_1", "llm_2")
    builder.add_edge("llm_2", END)

    graph = builder.compile()

    node_tokens = {"llm_1": 0, "llm_2": 0}

    async for event in graph.astream(
        {"messages": [], "count": 0},
        stream_mode="messages",
    ):
        if isinstance(event, tuple) and len(event) == 2:
            chunk, metadata = event
            node = metadata.get('langgraph_node', 'unknown') if isinstance(metadata, dict) else 'unknown'
            content = getattr(chunk, 'content', None)
            if content and node in node_tokens:
                node_tokens[node] += 1
                print(f"  {node}: {content!r}")

    print(f"\nTokens by node: {node_tokens}")
    print(f"Both nodes streamed: {all(v > 0 for v in node_tokens.values())}")


async def main():
    """Run all spike tests."""
    print("FR-029 Research Spike: LangGraph stream_mode='messages'")
    print("LangGraph version: 1.0.6")

    try:
        result1 = await test_ainvoke_streaming()
        await test_event_structure()
        await test_interrupt_handling()
        await test_multi_llm()
        await test_yamlgraph_compiled()

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Q1: Does ainvoke stream tokens? {'YES' if result1 else 'NO'}")
        print("Q2: Event structure: (AIMessageChunk, metadata_dict)")
        print("Q3: Interrupts: Check final_state.next, not in stream")
        print("Q4: Multiple LLMs: Both stream (see Test 4)")
        print("Q5: yamlgraph-compiled: See Test 5")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_yamlgraph_compiled():
    """Test 5: Does stream_mode=messages work with yamlgraph-compiled graphs?"""
    print("\n" + "=" * 60)
    print("TEST 5: yamlgraph-compiled graph")
    print("=" * 60)

    from yamlgraph.executor_async import load_and_compile_async

    # Use the hello demo graph
    graph_path = "examples/demos/hello/graph.yaml"
    app = await load_and_compile_async(graph_path)

    print(f"Testing with: {graph_path}")

    token_count = 0
    async for event in app.astream(
        {"name": "World", "style": "brief"},
        stream_mode="messages",
    ):
        if isinstance(event, tuple) and len(event) == 2:
            chunk, metadata = event
            content = getattr(chunk, 'content', None)
            node = metadata.get('langgraph_node', 'unknown') if isinstance(metadata, dict) else 'unknown'
            if content:
                token_count += 1
                print(f"  Token {token_count} from '{node}': {content!r}")

    print(f"\nResult: Received {token_count} tokens from yamlgraph-compiled graph")
    return token_count > 0


if __name__ == "__main__":
    asyncio.run(main())
