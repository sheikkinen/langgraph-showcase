"""Tests for async/streaming prompt resolution context.

These tests validate the bug where execute_prompt_async and
execute_prompt_streaming don't pass graph_path, prompts_dir,
prompts_relative to prepare_messages - causing graph-relative
prompt resolution to fail.
"""

import inspect
from pathlib import Path
from unittest.mock import patch

import pytest


class TestAsyncPromptResolutionArgs:
    """Tests for execute_prompt_async parameter handling."""

    def test_execute_prompt_async_accepts_graph_path(self) -> None:
        """Test that execute_prompt_async accepts graph_path parameter.

        Bug: The function signature doesn't include graph_path,
        so graphs using prompts_relative: true will fail in async context.
        """
        from yamlgraph.executor_async import execute_prompt_async

        sig = inspect.signature(execute_prompt_async)
        param_names = list(sig.parameters.keys())

        assert "graph_path" in param_names, (
            "execute_prompt_async should accept graph_path parameter "
            "for graph-relative prompt resolution"
        )

    def test_execute_prompt_async_accepts_prompts_dir(self) -> None:
        """Test that execute_prompt_async accepts prompts_dir parameter."""
        from yamlgraph.executor_async import execute_prompt_async

        sig = inspect.signature(execute_prompt_async)
        param_names = list(sig.parameters.keys())

        assert (
            "prompts_dir" in param_names
        ), "execute_prompt_async should accept prompts_dir parameter"

    def test_execute_prompt_async_accepts_prompts_relative(self) -> None:
        """Test that execute_prompt_async accepts prompts_relative parameter."""
        from yamlgraph.executor_async import execute_prompt_async

        sig = inspect.signature(execute_prompt_async)
        param_names = list(sig.parameters.keys())

        assert (
            "prompts_relative" in param_names
        ), "execute_prompt_async should accept prompts_relative parameter"

    def test_execute_prompt_async_passes_graph_path_to_prepare_messages(
        self,
    ) -> None:
        """Test that graph_path is passed to prepare_messages."""
        from yamlgraph.executor_async import execute_prompt_async

        # This test will fail until the bug is fixed
        with (
            patch("yamlgraph.executor_async.prepare_messages") as mock_prepare,
            patch("yamlgraph.executor_async.create_llm"),
            patch("yamlgraph.executor_async.invoke_async"),
        ):
            mock_prepare.return_value = ([], "anthropic", "claude-3-5-sonnet-20241022")

            # Try to call with graph_path - should not raise TypeError
            import asyncio

            try:
                asyncio.run(
                    execute_prompt_async(
                        "test_prompt",
                        variables={"x": 1},
                        graph_path=Path("/test/graph.yaml"),
                    )
                )
            except TypeError as e:
                if "graph_path" in str(e):
                    pytest.fail(
                        "execute_prompt_async does not accept graph_path: " f"{e}"
                    )
                raise


class TestStreamingPromptResolutionArgs:
    """Tests for execute_prompt_streaming parameter handling."""

    def test_execute_prompt_streaming_accepts_graph_path(self) -> None:
        """Test that execute_prompt_streaming accepts graph_path parameter."""
        from yamlgraph.executor_async import execute_prompt_streaming

        sig = inspect.signature(execute_prompt_streaming)
        param_names = list(sig.parameters.keys())

        assert "graph_path" in param_names, (
            "execute_prompt_streaming should accept graph_path parameter "
            "for graph-relative prompt resolution"
        )

    def test_execute_prompt_streaming_accepts_prompts_dir(self) -> None:
        """Test that execute_prompt_streaming accepts prompts_dir parameter."""
        from yamlgraph.executor_async import execute_prompt_streaming

        sig = inspect.signature(execute_prompt_streaming)
        param_names = list(sig.parameters.keys())

        assert (
            "prompts_dir" in param_names
        ), "execute_prompt_streaming should accept prompts_dir parameter"

    def test_execute_prompt_streaming_accepts_prompts_relative(self) -> None:
        """Test that execute_prompt_streaming accepts prompts_relative."""
        from yamlgraph.executor_async import execute_prompt_streaming

        sig = inspect.signature(execute_prompt_streaming)
        param_names = list(sig.parameters.keys())

        assert (
            "prompts_relative" in param_names
        ), "execute_prompt_streaming should accept prompts_relative parameter"


class TestSyncVsAsyncParity:
    """Tests ensuring sync and async have same resolution capabilities."""

    def test_sync_and_async_have_same_prompt_resolution_params(self) -> None:
        """Verify sync and async executors accept same prompt resolution params.

        execute_prompt (sync) accepts: graph_path, prompts_dir, prompts_relative
        execute_prompt_async should accept the same.
        """
        from yamlgraph.executor import execute_prompt
        from yamlgraph.executor_async import execute_prompt_async

        sync_sig = inspect.signature(execute_prompt)
        async_sig = inspect.signature(execute_prompt_async)

        # These are the prompt resolution parameters from sync executor
        resolution_params = {"graph_path", "prompts_dir", "prompts_relative"}

        sync_params = set(sync_sig.parameters.keys())
        async_params = set(async_sig.parameters.keys())

        # Check sync has them (should pass)
        missing_in_sync = resolution_params - sync_params
        assert not missing_in_sync, f"Sync executor missing: {missing_in_sync}"

        # Check async has them (this is the bug - should fail until fixed)
        missing_in_async = resolution_params - async_params
        assert not missing_in_async, (
            f"Async executor missing prompt resolution params: {missing_in_async}. "
            "This breaks graph-relative prompt resolution in async context."
        )
