"""OpenAI-compatible Pydantic models."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    """OpenAI chat message."""

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI chat completion request.

    Accepts extra fields (reasoning_effort, stream_options, tools, etc.)
    to remain compatible with different OpenAI SDK versions.
    """

    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    tools: list[Any] | None = None


class Choice(BaseModel):
    """Single completion choice."""

    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    """Token usage stats."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage
