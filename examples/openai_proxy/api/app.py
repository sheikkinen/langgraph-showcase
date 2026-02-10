"""OpenAI-compatible guardrail proxy API server."""

import json
import logging
import os
import time
import uuid
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from examples.openai_proxy.api.models import (
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    Usage,
)

load_dotenv()  # .env for local testing; Fly.io uses secrets

logger = logging.getLogger(__name__)
security = HTTPBearer()


def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Verify bearer token against WEB_API_KEY env var."""
    web_api_key = os.environ.get("WEB_API_KEY", "")
    if not web_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WEB_API_KEY not configured",
        )
    if credentials.credentials != web_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    return credentials.credentials


def run_graph(*, initial_state: dict[str, Any]) -> dict[str, Any]:
    """Run the guardrail graph synchronously.

    In production this calls YAMLGraph's compiled graph.
    For testing this function is patched.
    """
    from yamlgraph.graph_loader import load_and_compile

    graph_path = os.getenv("GRAPH_PATH", "examples/openai_proxy/graph.yaml")
    state_graph = load_and_compile(graph_path)
    compiled = state_graph.compile()
    result = compiled.invoke(initial_state)
    return result


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    from examples.openai_proxy.api.models import ChatCompletionRequest

    app = FastAPI(title="YAMLGraph Guardrail Proxy", version="0.1.0")

    @app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
    def chat_completions(
        request: ChatCompletionRequest,
        _token: str = Depends(verify_token),
    ):
        if request.stream:
            raise HTTPException(400, "Streaming not supported in v1")

        # Serialize messages as JSON input to graph
        messages_json = json.dumps([m.model_dump() for m in request.messages])

        result = run_graph(initial_state={"input": messages_json})
        content = result.get("response", "")

        return ChatCompletionResponse(
            id=f"chatcmpl-yg-{uuid.uuid4().hex[:12]}",
            created=int(time.time()),
            model=request.model,
            choices=[Choice(message=ChatMessage(role="assistant", content=content))],
            usage=Usage(),
        )

    @app.get("/v1/models")
    def list_models(_token: str = Depends(verify_token)):
        provider = os.getenv("PROVIDER", "anthropic")
        model = os.getenv(f"{provider.upper()}_MODEL", "default")
        return {
            "object": "list",
            "data": [
                {
                    "id": model,
                    "object": "model",
                    "created": 0,
                    "owned_by": "yamlgraph",
                }
            ],
        }

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


# Module-level app instance for uvicorn (Fly.io CMD)
app = create_app()
