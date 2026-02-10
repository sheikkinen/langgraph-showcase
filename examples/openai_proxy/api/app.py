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
    from starlette.requests import Request
    from starlette.responses import Response

    from examples.openai_proxy.api.models import ChatCompletionRequest

    app = FastAPI(title="YAMLGraph Guardrail Proxy", version="0.1.0")

    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        """Log every incoming request — headers, method, path, body on errors."""
        headers = dict(request.headers)
        # Mask the token value but show its prefix for debugging
        auth = headers.get("authorization", "")
        if auth:
            parts = auth.split(" ", 1)
            scheme = parts[0] if parts else ""
            token = parts[1] if len(parts) > 1 else ""
            masked = f"{token[:8]}...{token[-4:]}" if len(token) > 12 else token
            headers["authorization"] = f"{scheme} {masked}"

        # Read body for error diagnostics
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8", errors="replace")[:4000]

        logger.info(
            "Incoming %s %s | headers=%s",
            request.method,
            request.url.path,
            json.dumps(headers, separators=(",", ":")),
        )
        response = await call_next(request)
        if response.status_code >= 400:
            logger.warning(
                "REQUEST FAILED %s %s -> %d | body=%s | headers=%s",
                request.method,
                request.url.path,
                response.status_code,
                body_text,
                json.dumps(headers, separators=(",", ":")),
            )
        return response

    @app.post("/v1/chat/completions")
    def chat_completions(
        request: ChatCompletionRequest,
        _token: str = Depends(verify_token),
    ):
        from starlette.responses import StreamingResponse

        chat_id = f"chatcmpl-yg-{uuid.uuid4().hex[:12]}"
        created = int(time.time())

        if request.stream:
            # Real token-by-token streaming via run_graph_streaming (FR-023)
            messages_json = json.dumps([m.model_dump() for m in request.messages])
            graph_path = os.getenv("GRAPH_PATH", "examples/openai_proxy/graph.yaml")

            async def stream_response():
                from yamlgraph.executor_async import run_graph_streaming

                first = True
                async for token in run_graph_streaming(
                    graph_path=graph_path,
                    initial_state={"input": messages_json},
                ):
                    chunk = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"role": "assistant", "content": token}
                                if first
                                else {"content": token},
                                "finish_reason": None,
                            }
                        ],
                    }
                    first = False
                    yield f"data: {json.dumps(chunk)}\n\n"
                # Final chunk with finish_reason
                done_chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(done_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
            )

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
