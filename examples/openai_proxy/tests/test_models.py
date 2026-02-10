"""Tests for OpenAI-compatible Pydantic models - TDD: Red phase."""

import pytest
from pydantic import ValidationError


class TestChatMessage:
    """Test ChatMessage model."""

    def test_create_user_message(self):
        """Should create a user message."""
        from examples.openai_proxy.api.models import ChatMessage

        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_create_assistant_message(self):
        """Should create an assistant message."""
        from examples.openai_proxy.api.models import ChatMessage

        msg = ChatMessage(role="assistant", content="Hi there")
        assert msg.role == "assistant"
        assert msg.content == "Hi there"

    def test_create_system_message(self):
        """Should create a system message."""
        from examples.openai_proxy.api.models import ChatMessage

        msg = ChatMessage(role="system", content="You are helpful")
        assert msg.role == "system"


class TestChatCompletionRequest:
    """Test ChatCompletionRequest model."""

    def test_minimal_request(self):
        """Should create request with required fields only."""
        from examples.openai_proxy.api.models import ChatCompletionRequest

        req = ChatCompletionRequest(
            model="claude-haiku-4-5",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert req.model == "claude-haiku-4-5"
        assert len(req.messages) == 1
        assert req.stream is False

    def test_full_request(self):
        """Should create request with all optional fields."""
        from examples.openai_proxy.api.models import ChatCompletionRequest

        req = ChatCompletionRequest(
            model="claude-haiku-4-5",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=100,
            stream=False,
        )
        assert req.temperature == 0.7
        assert req.max_tokens == 100

    def test_missing_model_raises(self):
        """Should require model field."""
        from examples.openai_proxy.api.models import ChatCompletionRequest

        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                messages=[{"role": "user", "content": "Hello"}],
            )

    def test_missing_messages_raises(self):
        """Should require messages field."""
        from examples.openai_proxy.api.models import ChatCompletionRequest

        with pytest.raises(ValidationError):
            ChatCompletionRequest(model="test-model")

    def test_empty_messages_list(self):
        """Should accept empty messages list (validation at API level)."""
        from examples.openai_proxy.api.models import ChatCompletionRequest

        req = ChatCompletionRequest(model="test", messages=[])
        assert len(req.messages) == 0


class TestChatCompletionResponse:
    """Test ChatCompletionResponse model."""

    def test_create_response(self):
        """Should create a valid completion response."""
        from examples.openai_proxy.api.models import (
            ChatCompletionResponse,
            ChatMessage,
            Choice,
            Usage,
        )

        resp = ChatCompletionResponse(
            id="chatcmpl-yg-abc123",
            created=1700000000,
            model="claude-haiku-4-5",
            choices=[
                Choice(
                    message=ChatMessage(role="assistant", content="Hello!"),
                )
            ],
            usage=Usage(),
        )
        assert resp.id == "chatcmpl-yg-abc123"
        assert resp.object == "chat.completion"
        assert resp.choices[0].message.content == "Hello!"
        assert resp.choices[0].finish_reason == "stop"

    def test_usage_defaults_to_zero(self):
        """Should default usage counters to zero."""
        from examples.openai_proxy.api.models import Usage

        usage = Usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_choice_defaults(self):
        """Should default index=0 and finish_reason='stop'."""
        from examples.openai_proxy.api.models import ChatMessage, Choice

        choice = Choice(message=ChatMessage(role="assistant", content="test"))
        assert choice.index == 0
        assert choice.finish_reason == "stop"
