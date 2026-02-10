"""Tests for per-node and default-level model override (REQ-YG-050).

Bug fix: `model` field in graph YAML node config and defaults was silently
ignored. Only `temperature` and `provider` were extracted from node_config.

The full call chain must pass `model`:
  create_node_function() → execute_prompt() → prepare_messages() → create_llm()

TDD RED phase — these tests MUST fail before the fix is applied.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from tests.conftest import FixtureGeneratedContent
from yamlgraph.node_factory import create_node_function

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_state():
    """Minimal state for node execution."""
    return {
        "thread_id": "test-model-override",
        "topic": "testing",
        "generated": None,
        "current_step": "init",
        "errors": [],
    }


class MockOutput(BaseModel):
    """Mock structured output."""

    text: str


# =============================================================================
# 1. Node-level model extraction (create_node_function)
# =============================================================================


class TestNodeModelOverride:
    """Model field must flow from graph YAML node config to execute_prompt."""

    @pytest.mark.req("REQ-YG-050")
    def test_node_config_model_passed_to_execute_prompt(self, sample_state):
        """Node-level `model` in config is passed to execute_prompt()."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "variables": {},
            "state_key": "generated",
        }
        mock_result = FixtureGeneratedContent(
            title="T", content="C", word_count=1, tags=[]
        )

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt",
            return_value=mock_result,
        ) as mock_exec:
            node_fn = create_node_function("generate", node_config, {})
            node_fn(sample_state)

            mock_exec.assert_called_once()
            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs["model"] == "claude-haiku-4-5"

    @pytest.mark.req("REQ-YG-050")
    def test_defaults_model_passed_to_execute_prompt(self, sample_state):
        """Defaults-level `model` is passed when node has no model."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "variables": {},
            "state_key": "generated",
        }
        defaults = {"provider": "mistral", "model": "mistral-small-latest"}

        mock_result = FixtureGeneratedContent(
            title="T", content="C", word_count=1, tags=[]
        )

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt",
            return_value=mock_result,
        ) as mock_exec:
            node_fn = create_node_function("generate", node_config, defaults)
            node_fn(sample_state)

            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs["model"] == "mistral-small-latest"

    @pytest.mark.req("REQ-YG-050")
    def test_node_model_overrides_defaults_model(self, sample_state):
        """Node-level model takes priority over defaults model."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "variables": {},
            "state_key": "generated",
        }
        defaults = {"provider": "anthropic", "model": "claude-sonnet-4-20250514"}

        mock_result = FixtureGeneratedContent(
            title="T", content="C", word_count=1, tags=[]
        )

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt",
            return_value=mock_result,
        ) as mock_exec:
            node_fn = create_node_function("generate", node_config, defaults)
            node_fn(sample_state)

            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs["model"] == "claude-haiku-4-5"

    @pytest.mark.req("REQ-YG-050")
    def test_no_model_passes_none(self, sample_state):
        """When neither node nor defaults specify model, None is passed."""
        node_config = {
            "type": "llm",
            "prompt": "generate",
            "variables": {},
            "state_key": "generated",
        }
        mock_result = FixtureGeneratedContent(
            title="T", content="C", word_count=1, tags=[]
        )

        with patch(
            "yamlgraph.node_factory.llm_nodes.execute_prompt",
            return_value=mock_result,
        ) as mock_exec:
            node_fn = create_node_function("generate", node_config, {})
            node_fn(sample_state)

            call_kwargs = mock_exec.call_args[1]
            assert "model" in call_kwargs, "model kwarg must be explicitly passed"
            assert call_kwargs["model"] is None


# =============================================================================
# 2. Sync executor model passthrough
# =============================================================================


class TestExecutorModelPassthrough:
    """execute_prompt() must accept and forward `model` to prepare_messages."""

    @pytest.mark.req("REQ-YG-050")
    def test_execute_prompt_accepts_model_kwarg(self):
        """Standalone execute_prompt() accepts model parameter."""
        from yamlgraph.executor import execute_prompt

        mock_result = MagicMock()
        mock_result.content = "hello"

        with (
            patch("yamlgraph.executor_base.load_prompt") as mock_load,
            patch("yamlgraph.executor.PromptExecutor._get_llm") as mock_llm,
            patch(
                "yamlgraph.executor.PromptExecutor._invoke_with_retry",
                return_value="hello",
            ),
        ):
            mock_load.return_value = {"system": "sys", "user": "hi {name}"}
            mock_llm.return_value = MagicMock()

            result = execute_prompt(
                "greet",
                variables={"name": "World"},
                model="claude-haiku-4-5",
            )

            assert result == "hello"
            # model should reach _get_llm
            mock_llm.assert_called_once()
            assert mock_llm.call_args[1]["model"] == "claude-haiku-4-5"

    @pytest.mark.req("REQ-YG-050")
    def test_executor_execute_passes_model_to_prepare_messages(self):
        """PromptExecutor.execute() forwards model to prepare_messages."""
        from yamlgraph.executor import PromptExecutor

        executor = PromptExecutor()

        with (
            patch("yamlgraph.executor_base.load_prompt") as mock_load,
            patch.object(executor, "_get_llm") as mock_llm,
            patch.object(executor, "_invoke_with_retry", return_value="ok"),
        ):
            mock_load.return_value = {"system": "sys", "user": "say {word}"}
            mock_llm.return_value = MagicMock()

            executor.execute(
                prompt_name="test",
                variables={"word": "hello"},
                model="mistral-small-latest",
            )

            # _get_llm should receive the model
            assert mock_llm.call_args[1]["model"] == "mistral-small-latest"


# =============================================================================
# 3. Async executor model passthrough
# =============================================================================


class TestAsyncExecutorModelPassthrough:
    """Async executors must accept and forward `model`."""

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-050")
    async def test_execute_prompt_async_accepts_model(self):
        """execute_prompt_async() accepts and forwards model."""
        from yamlgraph.executor_async import execute_prompt_async

        with (
            patch(
                "yamlgraph.executor_async.create_llm", return_value=MagicMock()
            ) as mock_create,
            patch(
                "yamlgraph.executor_async.invoke_async",
                new_callable=AsyncMock,
                return_value="streamed",
            ),
            patch("yamlgraph.executor_base.load_prompt") as mock_load,
        ):
            mock_load.return_value = {"system": "sys", "user": "hi {name}"}

            result = await execute_prompt_async(
                "greet",
                variables={"name": "World"},
                model="gemini-2.5-flash",
            )

            assert result == "streamed"
            assert mock_create.call_args[1]["model"] == "gemini-2.5-flash"

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-050")
    async def test_execute_prompt_streaming_accepts_model(self):
        """execute_prompt_streaming() accepts and forwards model."""
        from yamlgraph.executor_async import execute_prompt_streaming

        mock_llm = MagicMock()

        async def fake_astream(messages):
            chunk = MagicMock()
            chunk.content = "token"
            yield chunk

        mock_llm.astream = fake_astream

        with (
            patch(
                "yamlgraph.executor_async.create_llm", return_value=mock_llm
            ) as mock_create,
            patch("yamlgraph.executor_base.load_prompt") as mock_load,
        ):
            mock_load.return_value = {"system": "sys", "user": "hi {name}"}

            tokens = []
            async for token in execute_prompt_streaming(
                "greet",
                variables={"name": "World"},
                model="gemini-2.5-flash",
            ):
                tokens.append(token)

            assert tokens == ["token"]
            assert mock_create.call_args[1]["model"] == "gemini-2.5-flash"
