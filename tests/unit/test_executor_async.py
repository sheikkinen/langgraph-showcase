"""Unit tests for async executor module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from yamlgraph.executor_async import execute_prompt_async, execute_prompts_concurrent
from yamlgraph.utils.llm_factory_async import shutdown_executor


class TestExecutePromptAsync:
    """Tests for execute_prompt_async function."""

    def teardown_method(self):
        """Clean up executor after each test."""
        shutdown_executor()

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-015")
    async def test_executes_prompt(self):
        """Should execute a prompt and return result."""
        with patch("yamlgraph.executor_async.invoke_async") as mock_invoke:
            mock_invoke.return_value = "Hello, World!"

            result = await execute_prompt_async(
                "greet",
                variables={"name": "World", "style": "friendly"},
            )

            assert result == "Hello, World!"
            mock_invoke.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-015")
    async def test_passes_output_model(self):
        """Should pass output model to invoke_async."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            greeting: str

        with patch("yamlgraph.executor_async.invoke_async") as mock_invoke:
            mock_invoke.return_value = TestModel(greeting="Hi")

            result = await execute_prompt_async(
                "greet",
                variables={"name": "Test", "style": "casual"},
                output_model=TestModel,
            )

            assert isinstance(result, TestModel)
            # Check output_model was passed (positional arg)
            call_args = mock_invoke.call_args
            assert call_args[0][2] is TestModel  # 3rd positional arg

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-015")
    async def test_validates_variables(self):
        """Should raise error for missing variables."""
        with pytest.raises(ValueError, match="Missing required variable"):
            await execute_prompt_async("greet", variables={})

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-015")
    async def test_uses_provider_from_yaml(self):
        """Should extract provider from YAML metadata."""
        with (
            patch("yamlgraph.executor_base.load_prompt") as mock_load,
            patch("yamlgraph.executor_async.invoke_async") as mock_invoke,
            patch("yamlgraph.executor_async.create_llm") as mock_create_llm,
        ):
            mock_load.return_value = {
                "system": "You are helpful.",
                "user": "Hello {name}",
                "provider": "mistral",
            }
            mock_invoke.return_value = "Response"
            mock_create_llm.return_value = MagicMock()

            await execute_prompt_async("test", variables={"name": "User"})

            mock_create_llm.assert_called_once()
            call_kwargs = mock_create_llm.call_args[1]
            assert call_kwargs["provider"] == "mistral"


class TestExecutePromptsConcurrent:
    """Tests for execute_prompts_concurrent function."""

    def teardown_method(self):
        """Clean up executor after each test."""
        shutdown_executor()

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-015")
    async def test_executes_multiple_prompts(self):
        """Should execute multiple prompts concurrently."""
        with patch(
            "yamlgraph.executor_async.execute_prompt_async", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = ["Result 1", "Result 2", "Result 3"]

            results = await execute_prompts_concurrent(
                [
                    {"prompt_name": "greet", "variables": {"name": "A", "style": "x"}},
                    {"prompt_name": "greet", "variables": {"name": "B", "style": "y"}},
                    {"prompt_name": "greet", "variables": {"name": "C", "style": "z"}},
                ]
            )

            assert len(results) == 3
            assert results == ["Result 1", "Result 2", "Result 3"]
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-015")
    async def test_preserves_order(self):
        """Should return results in same order as input."""
        with patch(
            "yamlgraph.executor_async.execute_prompt_async", new_callable=AsyncMock
        ) as mock_execute:
            # Simulate varying response times
            async def delayed_response(prompt_name, **kwargs):
                name = kwargs.get("variables", {}).get("name", "")
                if name == "slow":
                    await asyncio.sleep(0.01)
                return f"Response for {name}"

            mock_execute.side_effect = delayed_response

            results = await execute_prompts_concurrent(
                [
                    {
                        "prompt_name": "greet",
                        "variables": {"name": "slow", "style": "a"},
                    },
                    {
                        "prompt_name": "greet",
                        "variables": {"name": "fast", "style": "b"},
                    },
                ]
            )

            assert results[0] == "Response for slow"
            assert results[1] == "Response for fast"

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-015")
    async def test_empty_list(self):
        """Should handle empty prompt list."""
        results = await execute_prompts_concurrent([])
        assert results == []

    @pytest.mark.asyncio
    @pytest.mark.req("REQ-YG-015")
    async def test_passes_all_options(self):
        """Should pass all options to execute_prompt_async."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            value: str

        with patch(
            "yamlgraph.executor_async.execute_prompt_async", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = TestModel(value="test")

            await execute_prompts_concurrent(
                [
                    {
                        "prompt_name": "test",
                        "variables": {"x": "y"},
                        "output_model": TestModel,
                        "temperature": 0.5,
                        "provider": "openai",
                    }
                ]
            )

            mock_execute.assert_called_once_with(
                prompt_name="test",
                variables={"x": "y"},
                output_model=TestModel,
                temperature=0.5,
                provider="openai",
            )
