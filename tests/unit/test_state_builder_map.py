"""Tests for state_builder map node reducer support."""

from typing import Annotated, get_args, get_origin

import pytest

from yamlgraph.models.state_builder import (
    build_state_class,
    extract_node_fields,
    sorted_add,
)


class TestExtractNodeFieldsMap:
    """Tests for map node collect field extraction."""

    @pytest.mark.req("REQ-YG-024", "REQ-YG-040")
    def test_map_node_collect_field_added(self) -> None:
        """Map node adds collect field to extracted fields."""
        nodes = {
            "expand_frames": {
                "type": "map",
                "over": "{state.frames}",
                "sub_node": "expand_frame",
                "collect": "expanded_frames",
            }
        }
        fields = extract_node_fields(nodes)
        assert "expanded_frames" in fields

    @pytest.mark.req("REQ-YG-024", "REQ-YG-040")
    def test_map_node_collect_has_sorted_reducer(self) -> None:
        """Map node collect field has Annotated[list, sorted_add] type."""
        nodes = {
            "expand_frames": {
                "type": "map",
                "over": "{state.frames}",
                "sub_node": "expand_frame",
                "collect": "expanded_frames",
            }
        }
        fields = extract_node_fields(nodes)

        field_type = fields["expanded_frames"]

        # Check it's Annotated
        assert get_origin(field_type) is Annotated
        # Check args: list and sorted_add for ordered fan-in
        args = get_args(field_type)
        assert args[0] is list
        assert args[1] is sorted_add

    @pytest.mark.req("REQ-YG-024", "REQ-YG-040")
    def test_map_node_without_collect_no_field(self) -> None:
        """Map node without collect key doesn't add field."""
        nodes = {
            "expand_frames": {
                "type": "map",
                "over": "{state.frames}",
                "sub_node": "expand_frame",
                # No collect key
            }
        }
        fields = extract_node_fields(nodes)
        # Should not have any fields from this node
        # (other fields may come from sub_node if it had output_key)
        assert "expanded_frames" not in fields


class TestBuildStateClassMap:
    """Tests for build_state_class with map nodes."""

    @pytest.mark.req("REQ-YG-024", "REQ-YG-040")
    def test_build_state_includes_collect_field(self) -> None:
        """Built state class includes map node collect field."""
        config = {
            "nodes": {
                "expand_frames": {
                    "type": "map",
                    "over": "{state.frames}",
                    "sub_node": "expand_frame",
                    "collect": "expanded_frames",
                }
            }
        }
        state_class = build_state_class(config)
        annotations = state_class.__annotations__

        assert "expanded_frames" in annotations

    @pytest.mark.req("REQ-YG-024", "REQ-YG-040")
    def test_build_state_collect_has_sorted_reducer(self) -> None:
        """Built state class has sorted_add reducer for collect field."""
        config = {
            "nodes": {
                "expand_frames": {
                    "type": "map",
                    "over": "{state.frames}",
                    "sub_node": "expand_frame",
                    "collect": "expanded_frames",
                }
            }
        }
        state_class = build_state_class(config)
        annotations = state_class.__annotations__

        field_type = annotations["expanded_frames"]
        assert get_origin(field_type) is Annotated
        args = get_args(field_type)
        assert args[0] is list
        assert args[1] is sorted_add
