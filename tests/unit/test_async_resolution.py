"""Tests for async/streaming graph-relative prompt resolution.

Gap: Async/streaming tests don't cover graph-relative prompt resolution
or custom prompts_dir, so regressions aren't exercised.

These tests validate the actual resolution behavior, not just signatures.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAsyncGraphRelativePromptResolution:
    """Tests for execute_prompt_async with graph-relative prompts."""

    @pytest.mark.asyncio
    async def test_async_resolves_prompt_relative_to_graph(self) -> None:
        """execute_prompt_async should resolve prompts relative to graph path."""
        from yamlgraph.executor_async import execute_prompt_async

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create graph and prompt in same directory
            # Note: prompts_relative=True with prompts_dir="prompts" looks in
            # graph_path.parent / prompts_dir / prompt_name.yaml
            graph_dir = Path(tmpdir)
            graph_path = graph_dir / "test_graph.yaml"
            prompts_subdir = graph_dir / "prompts"
            prompts_subdir.mkdir()

            # Create a prompt file
            prompt_file = prompts_subdir / "relative_test.yaml"
            prompt_file.write_text(
                "system: You are a test assistant.\nuser: Process {input}\n"
            )

            with (
                patch("yamlgraph.executor_async.create_llm") as mock_create_llm,
                patch("yamlgraph.executor_async.invoke_async") as mock_invoke,
            ):
                mock_llm = MagicMock()
                mock_create_llm.return_value = mock_llm
                mock_invoke.return_value = "Result"

                # Should resolve prompt relative to graph with prompts_dir
                result = await execute_prompt_async(
                    "relative_test",
                    variables={"input": "test"},
                    graph_path=graph_path,
                    prompts_dir=Path("prompts"),
                    prompts_relative=True,
                )

                assert result == "Result"
                # Verify it actually loaded the prompt (mock_invoke was called)
                mock_invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_uses_custom_prompts_dir(self) -> None:
        """execute_prompt_async should use custom prompts_dir."""
        from yamlgraph.executor_async import execute_prompt_async

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_prompts = Path(tmpdir) / "custom_prompts"
            custom_prompts.mkdir()

            prompt_file = custom_prompts / "custom_test.yaml"
            prompt_file.write_text(
                """
system: Custom system prompt.
user: Custom user {input}
"""
            )

            with (
                patch("yamlgraph.executor_async.create_llm") as mock_create_llm,
                patch("yamlgraph.executor_async.invoke_async") as mock_invoke,
            ):
                mock_create_llm.return_value = MagicMock()
                mock_invoke.return_value = "Custom result"

                result = await execute_prompt_async(
                    "custom_test",
                    variables={"input": "data"},
                    prompts_dir=custom_prompts,
                )

                assert result == "Custom result"
                mock_invoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_graph_path_takes_effect(self) -> None:
        """Verify graph_path actually affects prompt resolution."""
        from yamlgraph.executor_async import execute_prompt_async

        with (
            patch("yamlgraph.executor_async.prepare_messages") as mock_prepare,
            patch("yamlgraph.executor_async.create_llm"),
            patch("yamlgraph.executor_async.invoke_async"),
        ):
            mock_prepare.return_value = ([], "anthropic", "claude")

            test_graph_path = Path("/test/graph.yaml")

            await execute_prompt_async(
                "test_prompt",
                variables={},
                graph_path=test_graph_path,
                prompts_relative=True,
            )

            # Verify prepare_messages received the graph_path
            mock_prepare.assert_called_once()
            call_kwargs = mock_prepare.call_args.kwargs

            assert (
                call_kwargs.get("graph_path") == test_graph_path
            ), f"graph_path not passed to prepare_messages. Got kwargs: {call_kwargs}"
            assert call_kwargs.get("prompts_relative") is True


class TestStreamingGraphRelativePromptResolution:
    """Tests for execute_prompt_streaming with graph-relative prompts."""

    @pytest.mark.asyncio
    async def test_streaming_resolves_prompt_relative_to_graph(self) -> None:
        """execute_prompt_streaming should resolve prompts relative to graph."""
        from yamlgraph.executor_async import execute_prompt_streaming

        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir)
            graph_path = graph_dir / "stream_graph.yaml"
            prompts_subdir = graph_dir / "prompts"
            prompts_subdir.mkdir()

            prompt_file = prompts_subdir / "stream_test.yaml"
            prompt_file.write_text("system: Streaming test.\nuser: Stream {input}\n")

            mock_chunk = MagicMock()
            mock_chunk.content = "streamed"

            async def mock_astream(*args, **kwargs):
                yield mock_chunk

            mock_llm = MagicMock()
            mock_llm.astream = mock_astream

            with patch("yamlgraph.executor_async.create_llm", return_value=mock_llm):
                tokens = []
                async for token in execute_prompt_streaming(
                    "stream_test",
                    variables={"input": "data"},
                    graph_path=graph_path,
                    prompts_dir=Path("prompts"),
                    prompts_relative=True,
                ):
                    tokens.append(token)

                assert tokens == ["streamed"]

    @pytest.mark.asyncio
    async def test_streaming_uses_custom_prompts_dir(self) -> None:
        """execute_prompt_streaming should use custom prompts_dir."""
        from yamlgraph.executor_async import execute_prompt_streaming

        with tempfile.TemporaryDirectory() as tmpdir:
            custom_prompts = Path(tmpdir) / "stream_prompts"
            custom_prompts.mkdir()

            prompt_file = custom_prompts / "stream_custom.yaml"
            prompt_file.write_text(
                """
system: Custom stream.
user: Stream custom {input}
"""
            )

            mock_chunk = MagicMock()
            mock_chunk.content = "custom_streamed"

            async def mock_astream(*args, **kwargs):
                yield mock_chunk

            mock_llm = MagicMock()
            mock_llm.astream = mock_astream

            with patch("yamlgraph.executor_async.create_llm", return_value=mock_llm):
                tokens = []
                async for token in execute_prompt_streaming(
                    "stream_custom",
                    variables={"input": "data"},
                    prompts_dir=custom_prompts,
                ):
                    tokens.append(token)

                assert tokens == ["custom_streamed"]

    @pytest.mark.asyncio
    async def test_streaming_graph_path_takes_effect(self) -> None:
        """Verify graph_path actually affects streaming prompt resolution."""
        from yamlgraph.executor_async import execute_prompt_streaming

        async def mock_astream(*args, **kwargs):
            mock_chunk = MagicMock()
            mock_chunk.content = "test"
            yield mock_chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream

        with (
            patch("yamlgraph.executor_async.prepare_messages") as mock_prepare,
            patch("yamlgraph.executor_async.create_llm", return_value=mock_llm),
        ):
            mock_prepare.return_value = ([], "anthropic", "claude")

            test_graph_path = Path("/test/stream_graph.yaml")

            async for _ in execute_prompt_streaming(
                "test_prompt",
                variables={},
                graph_path=test_graph_path,
                prompts_relative=True,
            ):
                pass

            mock_prepare.assert_called_once()
            call_kwargs = mock_prepare.call_args.kwargs

            assert call_kwargs.get("graph_path") == test_graph_path
            assert call_kwargs.get("prompts_relative") is True


class TestPromptResolutionPriorityAsync:
    """Tests for prompt resolution priority in async executor."""

    @pytest.mark.asyncio
    async def test_prompts_dir_overrides_default_resolution(self) -> None:
        """prompts_dir should override default prompts/ directory."""
        from yamlgraph.executor_async import execute_prompt_async

        with (
            patch("yamlgraph.executor_async.prepare_messages") as mock_prepare,
            patch("yamlgraph.executor_async.create_llm"),
            patch("yamlgraph.executor_async.invoke_async"),
        ):
            mock_prepare.return_value = ([], "anthropic", "claude")

            custom_dir = Path("/custom/prompts")

            await execute_prompt_async(
                "my_prompt",
                variables={},
                prompts_dir=custom_dir,
            )

            call_kwargs = mock_prepare.call_args.kwargs
            assert call_kwargs.get("prompts_dir") == custom_dir

    @pytest.mark.asyncio
    async def test_graph_relative_with_prompts_dir_combined(self) -> None:
        """graph_path and prompts_dir can be used together."""
        from yamlgraph.executor_async import execute_prompt_async

        with (
            patch("yamlgraph.executor_async.prepare_messages") as mock_prepare,
            patch("yamlgraph.executor_async.create_llm"),
            patch("yamlgraph.executor_async.invoke_async"),
        ):
            mock_prepare.return_value = ([], "anthropic", "claude")

            graph_path = Path("/project/graphs/main.yaml")
            prompts_dir = Path("/project/shared/prompts")

            await execute_prompt_async(
                "shared_prompt",
                variables={},
                graph_path=graph_path,
                prompts_dir=prompts_dir,
                prompts_relative=False,  # Use explicit prompts_dir
            )

            call_kwargs = mock_prepare.call_args.kwargs
            assert call_kwargs.get("graph_path") == graph_path
            assert call_kwargs.get("prompts_dir") == prompts_dir
            assert call_kwargs.get("prompts_relative") is False
