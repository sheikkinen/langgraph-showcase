"""Tests for the OpenAI-compatible API server - TDD: Red phase."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def web_api_key():
    """Set WEB_API_KEY env var for tests."""
    key = "test-secret-key-123"
    with patch.dict(os.environ, {"WEB_API_KEY": key}):
        yield key


@pytest.fixture
def client(web_api_key):
    """Create test client with WEB_API_KEY set."""
    # Reimport to pick up patched env
    from examples.openai_proxy.api.app import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers(web_api_key):
    """Authorization headers with valid token."""
    return {"Authorization": f"Bearer {web_api_key}"}


class TestAuth:
    """Test Bearer token authentication."""

    def test_no_token_returns_unauthorized(self, client):
        """Should reject requests without token."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "test",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code in (401, 403)

    def test_wrong_token_returns_401(self, client):
        """Should return 401 for invalid token."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "test",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401

    def test_valid_token_accepted(self, client, auth_headers):
        """Should accept valid token (graph mock needed for full test)."""
        with patch(
            "examples.openai_proxy.api.app.run_graph",
            return_value={"response": "Hi there"},
        ):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "test",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
                headers=auth_headers,
            )
            assert response.status_code == 200

    def test_missing_web_api_key_env_returns_500(self):
        """Should return 500 when WEB_API_KEY not configured."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("WEB_API_KEY", None)
            from examples.openai_proxy.api.app import create_app

            app = create_app()
            test_client = TestClient(app)
            response = test_client.post(
                "/v1/chat/completions",
                json={
                    "model": "test",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
                headers={"Authorization": "Bearer anything"},
            )
            assert response.status_code == 500


class TestChatCompletions:
    """Test POST /v1/chat/completions endpoint."""

    def test_returns_openai_format(self, client, auth_headers):
        """Should return response in OpenAI ChatCompletion format."""
        with patch(
            "examples.openai_proxy.api.app.run_graph",
            return_value={"response": "Hello from YAMLGraph!"},
        ):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "claude-haiku-4-5",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["object"] == "chat.completion"
            assert data["model"] == "claude-haiku-4-5"
            assert len(data["choices"]) == 1
            assert data["choices"][0]["message"]["role"] == "assistant"
            assert data["choices"][0]["message"]["content"] == "Hello from YAMLGraph!"
            assert data["choices"][0]["finish_reason"] == "stop"
            assert "id" in data
            assert data["id"].startswith("chatcmpl-yg-")
            assert "usage" in data

    def test_passes_messages_as_json_to_graph(self, client, auth_headers):
        """Should serialize messages as JSON input to graph."""
        mock_run = MagicMock(return_value={"response": "ok"})
        with patch("examples.openai_proxy.api.app.run_graph", mock_run):
            client.post(
                "/v1/chat/completions",
                json={
                    "model": "test",
                    "messages": [
                        {"role": "system", "content": "Be helpful"},
                        {"role": "user", "content": "Hi"},
                    ],
                },
                headers=auth_headers,
            )
            call_args = mock_run.call_args
            input_data = call_args[1].get(
                "initial_state", call_args[0][0] if call_args[0] else {}
            )
            if isinstance(input_data, dict):
                messages = json.loads(input_data["input"])
                assert len(messages) == 2
                assert messages[0]["role"] == "system"

    @pytest.mark.req("REQ-YG-049")
    def test_streaming_returns_sse(self, client, auth_headers):
        """Should return SSE stream for streaming requests (FR-023)."""

        async def mock_stream(*args, **kwargs):
            yield "Hello"
            yield " world"

        with patch(
            "yamlgraph.executor_async.run_graph_streaming",
            side_effect=mock_stream,
        ):
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "test",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            body = response.text
            assert "data: " in body
            assert "data: [DONE]" in body


class TestModels:
    """Test GET /v1/models endpoint."""

    def test_list_models(self, client, auth_headers):
        """Should return configured model from env."""
        with patch.dict(
            os.environ,
            {"PROVIDER": "anthropic", "ANTHROPIC_MODEL": "claude-haiku-4-5"},
        ):
            response = client.get("/v1/models", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["object"] == "list"
            assert len(data["data"]) == 1
            assert data["data"][0]["id"] == "claude-haiku-4-5"
            assert data["data"][0]["object"] == "model"


class TestHealth:
    """Test GET /health endpoint."""

    def test_health_endpoint(self, client):
        """Should return health status (no auth required)."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
