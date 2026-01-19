# Feature Request: Async Executor

**ID:** 003  
**Priority:** P2 - High  
**Status:** ✅ Implemented  
**Effort:** 3 days  
**Requested:** 2026-01-19  
**Implemented:** 2026-01-19  
**Commit:** `77d5747`  
**Docs:** [reference/async-usage.md](../reference/async-usage.md)

## Summary

Provide full async support for graph execution, enabling native integration with async web frameworks like FastAPI.

## Motivation

Current YamlGraph executor is primarily synchronous. Web APIs using FastAPI, Starlette, or aiohttp need async to:
- Handle concurrent requests efficiently
- Avoid blocking the event loop
- Integrate with async ORMs, Redis, etc.

**Use case:** questionnaire-api runs on FastAPI with async Redis sessions. Graph execution should not block.

## Current State

`yamlgraph/executor_async.py` exists but is limited:
- Only wraps sync execution
- Doesn't leverage LangGraph's native async

## Proposed Solution

### API

```python
from yamlgraph import load_and_compile
from yamlgraph.executor_async import run_graph_async, run_until_interrupt_async

# Async execution
async def handle_message(session_id: str, message: str):
    graph = load_and_compile("graphs/interview.yaml")
    
    result = await run_until_interrupt_async(
        graph=graph,
        state={"user_message": message},
        config={"configurable": {"thread_id": session_id}},
    )
    
    return result["state"]["response"]
```

### FastAPI Integration

```python
from fastapi import FastAPI
from yamlgraph import load_and_compile
from yamlgraph.executor_async import run_until_interrupt_async

app = FastAPI()
graph = load_and_compile("graphs/interview.yaml")

@app.post("/message")
async def process_message(request: MessageRequest):
    result = await run_until_interrupt_async(
        graph=graph,
        state={"user_message": request.message},
        config={"configurable": {"thread_id": request.session_id}},
    )
    
    return {
        "response": result["state"]["response"],
        "complete": result["status"] == "complete",
    }
```

### Implementation

```python
# yamlgraph/executor_async.py
from typing import Any, AsyncIterator

async def run_graph_async(
    graph,
    initial_state: dict,
    config: dict,
) -> dict:
    """Execute graph asynchronously to completion."""
    app = graph.compile(checkpointer=config.get("checkpointer"))
    
    final_state = None
    async for event in app.astream(initial_state, config):
        final_state = event
    
    return {"status": "complete", "state": final_state}


async def run_until_interrupt_async(
    graph,
    initial_state: dict,
    config: dict,
) -> dict:
    """Execute graph until completion or interrupt."""
    app = graph.compile(checkpointer=config.get("checkpointer"))
    
    async for event in app.astream(initial_state, config):
        if event.get("_interrupt"):
            return {
                "status": "interrupted",
                "thread_id": config["configurable"]["thread_id"],
                "state": event,
                "resume_key": event.get("_resume_key"),
            }
    
    return {"status": "complete", "state": event}


async def resume_async(
    graph,
    thread_id: str,
    resume_data: dict,
    config: dict | None = None,
) -> dict:
    """Resume interrupted graph with new input."""
    config = config or {}
    config.setdefault("configurable", {})["thread_id"] = thread_id
    
    # Merge resume data into state
    return await run_until_interrupt_async(graph, resume_data, config)


async def stream_graph_async(
    graph,
    initial_state: dict,
    config: dict,
) -> AsyncIterator[dict]:
    """Stream graph events asynchronously."""
    app = graph.compile(checkpointer=config.get("checkpointer"))
    
    async for event in app.astream(initial_state, config):
        yield event
```

### Async Prompt Execution

```python
# yamlgraph/executor.py
async def execute_prompt_async(
    prompt_name: str,
    variables: dict,
    state: dict | None = None,
    **kwargs,
) -> Any:
    """Execute prompt asynchronously."""
    prompt_data = load_prompt(prompt_name)
    llm = create_llm(**kwargs)
    
    messages = build_messages(prompt_data, variables, state)
    
    # Use async invoke
    response = await llm.ainvoke(messages)
    
    return parse_response(response, kwargs.get("response_model"))
```

## Changes Required

1. **executor_async.py** - Full rewrite with native async
2. **node_factory.py** - Async node function creation
3. **graph_loader.py** - Async compile option
4. **executor.py** - Async prompt execution

## Acceptance Criteria

- [ ] `run_graph_async()` uses native `astream()`
- [ ] `run_until_interrupt_async()` works with interrupt nodes
- [ ] `resume_async()` continues from checkpoint
- [ ] `stream_graph_async()` yields events
- [ ] `execute_prompt_async()` for async LLM calls
- [ ] Works with Redis checkpointer
- [ ] FastAPI example in docs
- [ ] No blocking calls in async code path
- [ ] Integration test with async Redis

## Related

- Feature #001: Interrupt Node
- Feature #002: Redis Checkpointer (async Redis client)
- Feature #004: Streaming Support (builds on async iterator)
