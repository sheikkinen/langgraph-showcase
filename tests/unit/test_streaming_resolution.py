"""Tests for streaming node prompt resolution and Jinja2 state.

Bug: Streaming nodes don't pass graph_path, prompts_dir, prompts_relative,
or state to execute_prompt_streaming, causing inconsistent behavior between
streaming and non-streaming nodes.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from yamlgraph.node_factory.streaming import create_streaming_node


class TestStreamingNodeResolution:
    """Tests for streaming node prompt resolution."""

    @pytest.mark.asyncio
    async def test_streaming_node_passes_graph_path(self) -> None:
        """Streaming node should pass graph_path for relative prompt resolution."""
        captured_calls = []

        async def capture_streaming(*args, **kwargs):
            captured_calls.append(kwargs)
            yield "token"

        with patch(
            "yamlgraph.executor_async.execute_prompt_streaming",
            side_effect=capture_streaming,
        ):
            node_fn = create_streaming_node(
                "streamer",
                {
                    "prompt": "generate",
                    "stream": True,
                },
                graph_path=Path("/test/graph.yaml"),
            )

            state = {"input": "test"}
            async for _ in node_fn(state):
                pass

            assert len(captured_calls) == 1
            call_kwargs = captured_calls[0]

            # graph_path should now be passed to execute_prompt_streaming
            assert "graph_path" in call_kwargs, (
                f"Streaming nodes should support graph_path for prompts_relative. "
                f"Got kwargs: {list(call_kwargs.keys())}"
            )
            assert call_kwargs["graph_path"] == Path("/test/graph.yaml")

    @pytest.mark.asyncio
    async def test_streaming_node_passes_state_for_jinja2(self) -> None:
        """Streaming node should pass state for Jinja2 {{ state.* }} templates."""
        captured_calls = []

        async def capture_streaming(*args, **kwargs):
            captured_calls.append(kwargs)
            yield "token"

        with patch(
            "yamlgraph.executor_async.execute_prompt_streaming",
            side_effect=capture_streaming,
        ):
            node_fn = create_streaming_node(
                "streamer",
                {
                    "prompt": "generate",
                    "stream": True,
                },
            )

            state = {"topic": "AI", "context": "research"}
            async for _ in node_fn(state):
                pass

            assert len(captured_calls) == 1
            call_kwargs = captured_calls[0]

            # Bug: state is not passed to execute_prompt_streaming
            assert "state" in call_kwargs, (
                f"Streaming nodes should pass state= for Jinja2 templates. "
                f"Got kwargs: {list(call_kwargs.keys())}"
            )
            assert call_kwargs.get("state") == state


class TestStreamingVsNonStreamingParity:
    """Tests for parity between streaming and non-streaming nodes."""

    def test_streaming_node_config_missing_resolution_params(self) -> None:
        """Streaming node creation doesn't accept prompt resolution params."""
        import inspect

        from yamlgraph.node_factory.streaming import create_streaming_node

        streaming_sig = inspect.signature(create_streaming_node)
        streaming_params = set(streaming_sig.parameters.keys())

        # Non-streaming create_node_function accepts these params
        expected_params = {"graph_path", "prompts_dir", "prompts_relative"}

        # Bug: create_streaming_node only accepts (node_name, node_config)
        missing = expected_params - streaming_params
        assert len(missing) == 0, (
            f"create_streaming_node is missing parameters for prompt resolution: {missing}. "
            f"Has: {streaming_params}"
        )

    @pytest.mark.asyncio
    async def test_streaming_dispatch_loses_resolution_context(self) -> None:
        """When llm_nodes dispatches to streaming, resolution context is lost."""
        # This test validates the dispatch in llm_nodes.py:57-60
        # if node_config.get("stream", False):
        #     return create_streaming_node(node_name, node_config)
        #
        # Notice: graph_path, prompts_dir, prompts_relative are NOT passed

        # The fix requires:
        # 1. create_streaming_node to accept these params
        # 2. llm_nodes to pass them when dispatching

        from yamlgraph.node_factory import create_node_function

        captured_streaming_calls = []

        async def capture_streaming(*args, **kwargs):
            captured_streaming_calls.append(kwargs)
            yield "token"

        with (
            patch(
                "yamlgraph.executor_async.execute_prompt_streaming",
                side_effect=capture_streaming,
            ),
        ):
            # Create streaming node via the normal dispatch path
            node_fn = create_node_function(
                "streamer",
                {
                    "type": "llm",
                    "prompt": "generate",
                    "stream": True,
                },
                defaults={"prompts_relative": True},
                graph_path=Path("/path/to/graph.yaml"),
            )

            # Execute the streaming node
            state = {"input": "test"}
            async for _ in node_fn(state):
                pass

            # Verify prompts_relative was passed through
            if captured_streaming_calls:
                call = captured_streaming_calls[0]
                # Bug: These params are not passed in current implementation
                assert (
                    call.get("prompts_relative") is True
                ), f"prompts_relative should propagate to streaming. Got: {call}"
