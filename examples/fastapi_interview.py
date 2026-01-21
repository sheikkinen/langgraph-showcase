"""FastAPI example with async graph execution.

Demonstrates:
- Async graph loading and compilation
- Interrupt handling via HTTP endpoints
- Thread-based session management

Run:
    pip install fastapi uvicorn
    uvicorn examples.fastapi_interview:app --reload

Usage:
    # Start a new session
    curl -X POST http://localhost:8000/chat/session1 -d '{"message": "start"}'

    # Resume after interrupt (provide user's name)
    curl -X POST http://localhost:8000/chat/session1/resume -d '{"answer": "Alice"}'
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from yamlgraph.executor_async import load_and_compile_async, run_graph_async

logger = logging.getLogger(__name__)

# Global compiled graph (loaded once at startup)
_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load graph at startup."""
    global _app
    try:
        _app = await load_and_compile_async("graphs/interview-demo.yaml")
        logger.info("✅ Graph loaded and compiled")
    except FileNotFoundError:
        logger.warning("⚠️ interview-demo.yaml not found, using mock mode")
        _app = None
    yield


app = FastAPI(
    title="YAMLGraph Interview Demo",
    description="Async interview graph with interrupt support",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    """Request to start or continue chat."""

    message: str = "start"


class ResumeRequest(BaseModel):
    """Request to resume after interrupt."""

    answer: str


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    status: str
    question: str | None = None
    response: str | None = None
    state: dict[str, Any] | None = None


@app.post("/chat/{thread_id}", response_model=ChatResponse)
async def chat(thread_id: str, request: ChatRequest) -> ChatResponse:
    """Start or continue a chat session.

    If graph hits an interrupt, returns status="waiting" with the question.
    Otherwise returns status="complete" with the response.
    """
    if _app is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await run_graph_async(
            _app,
            initial_state={"input": request.message},
            config=config,
        )
    except Exception as e:
        logger.error(f"Graph execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Check for interrupt
    if "__interrupt__" in result:
        interrupt_value = result["__interrupt__"][0].value
        question = interrupt_value.get("question") or interrupt_value.get(
            "prompt", str(interrupt_value)
        )
        return ChatResponse(
            status="waiting",
            question=question,
            state={k: v for k, v in result.items() if not k.startswith("_")},
        )

    return ChatResponse(
        status="complete",
        response=result.get("greeting") or result.get("response"),
        state={k: v for k, v in result.items() if not k.startswith("_")},
    )


@app.post("/chat/{thread_id}/resume", response_model=ChatResponse)
async def resume(thread_id: str, request: ResumeRequest) -> ChatResponse:
    """Resume a paused chat session with user's answer.

    Uses LangGraph's Command(resume=...) to continue execution.
    """
    if _app is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await run_graph_async(
            _app,
            initial_state=Command(resume=request.answer),
            config=config,
        )
    except Exception as e:
        logger.error(f"Graph resume error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Check for another interrupt
    if "__interrupt__" in result:
        interrupt_value = result["__interrupt__"][0].value
        question = interrupt_value.get("question") or interrupt_value.get(
            "prompt", str(interrupt_value)
        )
        return ChatResponse(
            status="waiting",
            question=question,
            state={k: v for k, v in result.items() if not k.startswith("_")},
        )

    return ChatResponse(
        status="complete",
        response=result.get("greeting") or result.get("response"),
        state={k: v for k, v in result.items() if not k.startswith("_")},
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "graph_loaded": _app is not None}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
