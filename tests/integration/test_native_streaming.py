"""Integration tests for native LangGraph streaming (FR-029 - REQ-YG-048, REQ-YG-065).

Tests run_graph_streaming_native() with actual yamlgraph-compiled graphs.
REQ-YG-048: Graph-level streaming yields LLM tokens
REQ-YG-065: Native streaming from all LLM nodes with node_filter
"""

import pytest

from yamlgraph.executor_async import run_graph_streaming_native


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-048")
@pytest.mark.req("REQ-YG-065")
async def test_native_streaming_hello_demo():
    """Stream tokens from hello demo graph."""
    tokens = []
    async for token in run_graph_streaming_native(
        "examples/demos/hello/graph.yaml",
        {"name": "World", "style": "brief"},
    ):
        tokens.append(token)

    # Should have received some tokens
    assert len(tokens) > 0
    # All tokens should be strings
    assert all(isinstance(t, str) for t in tokens)
    # Combined should form a greeting
    combined = "".join(tokens)
    assert len(combined) > 0


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-048")
@pytest.mark.req("REQ-YG-065")
async def test_native_streaming_with_config():
    """Stream with config (thread_id) for checkpointing."""
    config = {"configurable": {"thread_id": "test-native-stream-1"}}

    tokens = []
    async for token in run_graph_streaming_native(
        "examples/demos/hello/graph.yaml",
        {"name": "Alice", "style": "formal"},
        config=config,
    ):
        tokens.append(token)

    assert len(tokens) > 0


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-048")
@pytest.mark.req("REQ-YG-065")
async def test_native_streaming_node_filter():
    """Verify node_filter only yields from specified node."""
    # The hello demo has a "greet" node
    tokens_filtered = []
    async for token in run_graph_streaming_native(
        "examples/demos/hello/graph.yaml",
        {"name": "Bob", "style": "casual"},
        node_filter="greet",
    ):
        tokens_filtered.append(token)

    # Should still get tokens from the greet node
    assert len(tokens_filtered) > 0


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-065")
async def test_native_streaming_node_filter_no_match():
    """Node filter with non-existent node yields nothing."""
    tokens = []
    async for token in run_graph_streaming_native(
        "examples/demos/hello/graph.yaml",
        {"name": "Test", "style": "brief"},
        node_filter="nonexistent_node",
    ):
        tokens.append(token)

    # No tokens because filter doesn't match any node
    assert tokens == []


@pytest.mark.asyncio
@pytest.mark.req("REQ-YG-065")
async def test_native_streaming_deprecation_warning_not_raised():
    """run_graph_streaming_native should NOT raise deprecation warning."""
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _ = [
            t
            async for t in run_graph_streaming_native(
                "examples/demos/hello/graph.yaml",
                {"name": "Test", "style": "brief"},
            )
        ]
        # No deprecation warning for native version
        deprecation_warnings = [
            x for x in w if issubclass(x.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) == 0
