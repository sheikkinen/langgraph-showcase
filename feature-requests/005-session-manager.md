# Feature Request: Graph Session Manager

**ID:** 005  
**Priority:** P3 - Medium  
**Status:** ⏸️ Deferred  
**Effort:** 1 week  
**Requested:** 2026-01-19  
**Note:** With interrupt nodes (001), checkpointers (002), and async executor (003), the core primitives are available. A high-level session manager may not be needed—see `examples/fastapi_interview.py` for usage patterns.

## Summary

Add a generic session management abstraction for stateful graph execution with interrupt/resume support. This is a **framework-level** feature—application-specific session handling (like questionnaire extraction) is built on top.

## Motivation

Using YamlGraph for multi-turn interactions currently requires:
- Manual graph loading and compilation
- Checkpointer configuration
- Thread ID management
- Interrupt/resume handling

A high-level session API simplifies this for any stateful graph application.

## Proposed Solution

### API

```python
from yamlgraph.sessions import GraphSessionManager

# Initialize manager (once at app startup)
manager = GraphSessionManager(
    graph_path="graphs/my-graph.yaml",
    checkpointer_config={
        "type": "redis",
        "url": "redis://localhost:6379",
        "ttl": 3600,
    },
)

# Create or get session
session = await manager.get_or_create(thread_id="user-123")

# Invoke graph with input
result = await session.invoke({"user_input": "hello"})
print(result.status)   # "interrupted" | "complete"
print(result.state)    # Full graph state dict
print(result.output)   # Value from output_key (if configured)

# Resume after interrupt
result = await session.invoke({"user_input": "next message"})

# Get current state
state = await session.get_state()

# Delete session
await manager.delete("user-123")

# Cleanup on shutdown
await manager.cleanup()
```

### Core Classes

```python
# yamlgraph/sessions/result.py
from dataclasses import dataclass
from typing import Any

@dataclass
class InvokeResult:
    """Result from graph invocation."""
    status: str                    # "interrupted" | "complete"
    state: dict[str, Any]          # Full graph state
    output: Any = None             # Optional extracted output
    resume_key: str | None = None  # Key for resume input (if interrupted)
```

```python
# yamlgraph/sessions/session.py
from typing import Any

class GraphSession:
    """Stateful graph execution session.
    
    Wraps a compiled graph with checkpointing and interrupt/resume.
    This is a generic session - applications can subclass for
    domain-specific behavior.
    """
    
    def __init__(
        self,
        thread_id: str,
        graph,
        checkpointer,
        output_key: str | None = None,
    ):
        self.thread_id = thread_id
        self.graph = graph
        self.checkpointer = checkpointer
        self.output_key = output_key
        self._last_state: dict = {}
    
    async def invoke(self, input_state: dict) -> InvokeResult:
        """Invoke graph with input, handling interrupts.
        
        Args:
            input_state: Input to merge into graph state
            
        Returns:
            InvokeResult with status, state, and optional output
        """
        from yamlgraph.executor_async import run_until_interrupt_async
        
        result = await run_until_interrupt_async(
            graph=self.graph,
            initial_state=input_state,
            config={
                "configurable": {"thread_id": self.thread_id},
                "checkpointer": self.checkpointer,
            },
        )
        
        self._last_state = result["state"]
        
        output = None
        if self.output_key and self.output_key in self._last_state:
            output = self._last_state[self.output_key]
        
        return InvokeResult(
            status=result["status"],
            state=self._last_state,
            output=output,
            resume_key=result.get("resume_key"),
        )
    
    async def get_state(self) -> dict:
        """Get current session state."""
        return self._last_state.copy()
    
    @property
    def is_complete(self) -> bool:
        """Check if graph execution is complete."""
        return self._last_state.get("_complete", False)
```

```python
# yamlgraph/sessions/manager.py
from typing import Optional

class GraphSessionManager:
    """Manage multiple graph sessions with checkpointing.
    
    Generic session manager - applications can subclass for
    domain-specific session handling.
    """
    
    def __init__(
        self,
        graph_path: str,
        checkpointer_config: dict | None = None,
        output_key: str | None = None,
    ):
        self.graph = load_and_compile(graph_path)
        self.checkpointer = get_checkpointer(checkpointer_config)
        self.output_key = output_key
        self._sessions: dict[str, GraphSession] = {}
    
    async def get_or_create(
        self,
        thread_id: str,
        initial_state: dict | None = None,
    ) -> GraphSession:
        """Get existing session or create new one."""
        if thread_id in self._sessions:
            return self._sessions[thread_id]
        
        session = GraphSession(
            thread_id=thread_id,
            graph=self.graph,
            checkpointer=self.checkpointer,
            output_key=self.output_key,
        )
        
        # Restore state from checkpointer if exists
        saved = await self.checkpointer.aget(
            {"configurable": {"thread_id": thread_id}}
        )
        if saved:
            session._last_state = saved.get("channel_values", {})
        elif initial_state:
            session._last_state = initial_state
        
        self._sessions[thread_id] = session
        return session
    
    async def get(self, thread_id: str) -> Optional[GraphSession]:
        """Get session if exists."""
        return self._sessions.get(thread_id) or await self._restore(thread_id)
    
    async def delete(self, thread_id: str) -> bool:
        """Delete session and its checkpoint."""
        self._sessions.pop(thread_id, None)
        await self.checkpointer.adelete(
            {"configurable": {"thread_id": thread_id}}
        )
        return True
    
    async def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        self._sessions.clear()
        if hasattr(self.checkpointer, 'cleanup'):
            await self.checkpointer.cleanup()
```

### Extension Point for Applications

Applications build on top of the generic session:

```python
# Example: questionnaire-api/src/api/sessions/yamlgraph_session.py
from yamlgraph.sessions import GraphSession, InvokeResult
from dataclasses import dataclass

@dataclass
class QuestionnaireResult(InvokeResult):
    """Questionnaire-specific result with extracted fields."""
    extracted: dict | None = None
    phase: str | None = None
    response: str = ""


class QuestionnaireSession(GraphSession):
    """Questionnaire-specific session wrapper."""
    
    async def send_message(self, message: str) -> QuestionnaireResult:
        """Send user message, get questionnaire response."""
        result = await self.invoke({"user_message": message})
        
        return QuestionnaireResult(
            status=result.status,
            state=result.state,
            output=result.output,
            resume_key=result.resume_key,
            # Questionnaire-specific fields
            extracted=result.state.get("extracted"),
            phase=result.state.get("phase"),
            response=result.state.get("response", ""),
        )
```

### FastAPI Example

```python
from fastapi import FastAPI, Depends
from yamlgraph.sessions import GraphSessionManager, GraphSession

app = FastAPI()
manager: GraphSessionManager = None

@app.on_event("startup")
async def startup():
    global manager
    manager = GraphSessionManager(
        graph_path="graphs/assistant.yaml",
        checkpointer_config={"type": "redis", "url": os.getenv("REDIS_URL")},
        output_key="response",
    )

@app.on_event("shutdown")
async def shutdown():
    await manager.cleanup()

@app.post("/invoke/{thread_id}")
async def invoke_graph(thread_id: str, input_data: dict):
    session = await manager.get_or_create(thread_id)
    result = await session.invoke(input_data)
    return {
        "status": result.status,
        "output": result.output,
        "complete": result.status == "complete",
    }
```

## Design Principles

1. **Generic over specific** - No domain logic in YamlGraph
2. **Composable** - Easy to subclass for application needs
3. **Minimal API** - `invoke()`, `get_state()`, `delete()`
4. **Stateless manager** - State lives in checkpointer, not memory

## Acceptance Criteria

- [ ] `GraphSession` class with invoke/get_state
- [ ] `GraphSessionManager` with get_or_create/delete
- [ ] `InvokeResult` dataclass (generic)
- [ ] Works with any checkpointer (Redis, SQLite)
- [ ] Session restoration from checkpoint
- [ ] Proper cleanup on shutdown
- [ ] Subclassing example in docs
- [ ] FastAPI integration example
- [ ] Thread-safe for concurrent access

## Related

- Feature #001: Interrupt Node (used by invoke)
- Feature #002: Redis Checkpointer (storage backend)
- Feature #003: Async Executor (async invoke)
