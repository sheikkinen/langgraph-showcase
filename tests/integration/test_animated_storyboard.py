"""Tests for animated storyboard graph."""

from unittest.mock import MagicMock, patch

from yamlgraph.graph_loader import compile_graph, load_graph_config


class TestAnimatedStoryboardGraph:
    """Tests for the animated-character-storyboard graph."""

    def test_config_loads(self) -> None:
        """Animated character storyboard config loads successfully."""
        config = load_graph_config("examples/storyboard/animated-character-graph.yaml")
        assert config.name == "animated-character-storyboard"
        assert "expand_story" in config.nodes
        assert "animate_panels" in config.nodes
        assert "generate_images" in config.nodes

    def test_animate_panels_is_map_node(self) -> None:
        """animate_panels node is type: map."""
        config = load_graph_config("examples/storyboard/animated-character-graph.yaml")
        animate_node = config.nodes["animate_panels"]

        assert animate_node["type"] == "map"
        assert animate_node["over"] == "{state.story.panels}"
        assert animate_node["as"] == "panel_prompt"
        assert animate_node["collect"] == "animated_panels"

    def test_graph_compiles(self) -> None:
        """Animated character storyboard graph compiles to StateGraph."""
        config = load_graph_config("examples/storyboard/animated-character-graph.yaml")

        with patch("yamlgraph.node_compiler.compile_map_node") as mock_compile_map:
            mock_map_edge_fn = MagicMock()
            mock_compile_map.return_value = (
                mock_map_edge_fn,
                "_map_animate_panels_sub",
            )

            compile_graph(config)

            # Should have called compile_map_node for animate_panels
            mock_compile_map.assert_called_once()
            call_args = mock_compile_map.call_args
            assert call_args[0][0] == "animate_panels"

    def test_state_has_animated_panels_sorted_reducer(self) -> None:
        """State class has sorted_add reducer for animated_panels."""
        from typing import Annotated, get_args, get_origin

        from yamlgraph.models.state_builder import build_state_class, sorted_add

        config = load_graph_config("examples/storyboard/animated-character-graph.yaml")
        state_class = build_state_class(config.raw_config)

        annotations = state_class.__annotations__
        assert "animated_panels" in annotations

        field_type = annotations["animated_panels"]
        assert get_origin(field_type) is Annotated
        args = get_args(field_type)
        assert args[0] is list
        assert args[1] is sorted_add
