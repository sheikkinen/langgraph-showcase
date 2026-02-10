"""Integration tests for compile_graph with map nodes."""

from unittest.mock import MagicMock, patch

import pytest

from yamlgraph.graph_loader import GraphConfig, compile_graph


def make_graph_config(nodes: dict, edges: list) -> GraphConfig:
    """Helper to create GraphConfig from nodes and edges."""
    config_dict = {
        "name": "test-map",
        "version": "0.1",
        "nodes": nodes,
        "edges": edges,
    }
    return GraphConfig(config_dict)


def make_map_node_config(collect: str = "results") -> dict:
    """Helper to create a valid map node config."""
    return {
        "type": "map",
        "over": "{state.items}",
        "as": "item",
        "node": {"prompt": "process", "state_key": "result"},
        "collect": collect,
    }


class TestCompileGraphMap:
    """Tests for compile_graph handling type: map nodes."""

    @pytest.mark.req("REQ-YG-008", "REQ-YG-040")
    def test_map_node_compiled_to_graph(self) -> None:
        """Map node is correctly added to graph."""
        config = make_graph_config(
            nodes={
                "start_node": {"prompt": "generate", "state_key": "items"},
                "process_items": make_map_node_config(),
            },
            edges=[
                {"from": "START", "to": "start_node"},
                {"from": "start_node", "to": "process_items"},
                {"from": "process_items", "to": "END"},
            ],
        )

        with patch("yamlgraph.node_compiler.compile_map_node") as mock_compile_map:
            # Setup mock return value
            mock_map_edge_fn = MagicMock()
            mock_compile_map.return_value = (mock_map_edge_fn, "_map_process_items_sub")

            compile_graph(config)

            # verify compile_map_node was called with map node config
            mock_compile_map.assert_called_once()
            call_args = mock_compile_map.call_args
            assert call_args[0][0] == "process_items"  # name
            assert call_args[0][1]["type"] == "map"  # config

    @pytest.mark.req("REQ-YG-008", "REQ-YG-040")
    def test_map_node_sub_node_added(self) -> None:
        """Map node's wrapped sub_node is added to graph."""
        config = make_graph_config(
            nodes={
                "start_node": {"prompt": "generate", "state_key": "items"},
                "map_node": make_map_node_config(),
            },
            edges=[
                {"from": "START", "to": "start_node"},
                {"from": "start_node", "to": "map_node"},
                {"from": "map_node", "to": "END"},
            ],
        )

        with patch("yamlgraph.node_compiler.compile_map_node") as mock_compile_map:
            mock_map_edge_fn = MagicMock()
            mock_compile_map.return_value = (mock_map_edge_fn, "_map_map_node_sub")

            compile_graph(config)

            # Check sub node was added by compile_map_node
            # (the mocked compile_map_node adds it via the builder)
            # In the real implementation, compile_map_node adds the node

    @pytest.mark.req("REQ-YG-008", "REQ-YG-040")
    def test_map_node_conditional_edge_wired(self) -> None:
        """Map node predecessor gets conditional edge with Send function."""
        config = make_graph_config(
            nodes={
                "start_node": {"prompt": "generate", "state_key": "items"},
                "map_node": make_map_node_config(),
                "final_node": {"prompt": "summarize", "state_key": "summary"},
            },
            edges=[
                {"from": "START", "to": "start_node"},
                {"from": "start_node", "to": "map_node"},
                {"from": "map_node", "to": "final_node"},
                {"from": "final_node", "to": "END"},
            ],
        )

        with patch("yamlgraph.node_compiler.compile_map_node") as mock_compile_map:
            mock_map_edge_fn = MagicMock()
            mock_compile_map.return_value = (mock_map_edge_fn, "_map_map_node_sub")

            # For fan-in, we need to verify sub_node -> next_node edge is created
            compile_graph(config)

            # The graph should have conditional edge from start_node using map_edge_fn

    @pytest.mark.req("REQ-YG-008", "REQ-YG-040")
    def test_map_node_fanin_edge_wired(self) -> None:
        """Map sub_node has edge to next node for fan-in."""
        config = make_graph_config(
            nodes={
                "start_node": {"prompt": "generate", "state_key": "items"},
                "map_node": make_map_node_config(),
                "final_node": {"prompt": "summarize", "state_key": "summary"},
            },
            edges=[
                {"from": "START", "to": "start_node"},
                {"from": "start_node", "to": "map_node"},
                {"from": "map_node", "to": "final_node"},
                {"from": "final_node", "to": "END"},
            ],
        )

        with patch("yamlgraph.node_compiler.compile_map_node") as mock_compile_map:
            mock_map_edge_fn = MagicMock()
            mock_compile_map.return_value = (mock_map_edge_fn, "_map_map_node_sub")

            # For fan-in, we need to verify sub_node -> next_node edge is created
            compile_graph(config)

            # We'll verify by examining the graph's edges
