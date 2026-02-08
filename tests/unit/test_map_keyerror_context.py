"""Tests for map node KeyError handling.

Bug: Map node fan-out throws raw KeyError when 'over' references a missing
path, with no node or expression context, making debugging hard.
"""

import pytest

from yamlgraph.utils.expressions import resolve_state_expression


class TestMapNodeKeyErrorContext:
    """Tests for map node error handling with context."""

    @pytest.mark.xfail(
        reason="resolve_state_expression doesn't add context - map_compiler wrapper does"
    )
    def test_resolve_state_expression_raw_keyerror(self) -> None:
        """resolve_state_expression throws raw KeyError without context."""
        state = {"existing": "value"}

        with pytest.raises(KeyError) as exc_info:
            resolve_state_expression("{missing_key}", state)

        # Bug: The error message is just the key name, no context
        error_message = str(exc_info.value)

        # A good error would include:
        # - The expression that failed
        # - Available keys in state
        # - Hint about the path
        has_context = "missing_key" in error_message and (
            "expression" in error_message.lower() or "state" in error_message.lower()
        )

        assert has_context, (
            f"KeyError should include expression context for debugging. "
            f"Got: {error_message}"
        )

    def test_resolve_nested_path_raw_keyerror(self) -> None:
        """Nested path resolution throws raw KeyError without path context."""
        state = {"story": {"title": "Test"}}  # Missing "panels"

        with pytest.raises(KeyError) as exc_info:
            resolve_state_expression("{story.panels}", state)

        error_message = str(exc_info.value)

        # Bug: Error just says "panels", not the full path or what exists
        has_path_context = "story.panels" in error_message or "story" in error_message

        assert (
            has_path_context
        ), f"KeyError for nested path should show full path. Got: {error_message}"

    def test_map_over_missing_key_error_context(self) -> None:
        """Map 'over' with missing key should provide node context."""
        from unittest.mock import MagicMock

        from yamlgraph.map_compiler import compile_map_node

        # Create minimal builder mock
        builder = MagicMock()
        builder.add_node = MagicMock()

        map_config = {
            "over": "{missing_items}",  # This key doesn't exist
            "as": "item",
            "collect": "results",
            "node": {
                "type": "llm",
                "prompt": "process",
            },
        }

        # Compile should succeed (config is valid)
        map_edge, _ = compile_map_node(
            "process_items",
            map_config,
            builder,
            defaults={},
        )

        # Execute the edge function with state missing the key
        state = {"other_data": "exists"}

        with pytest.raises(KeyError) as exc_info:
            map_edge(state)

        error_message = str(exc_info.value)

        # Bug: Error is raw "missing_items" with no map node context
        has_map_context = (
            "process_items" in error_message
            or "map" in error_message.lower()
            or "over" in error_message.lower()
        )

        assert has_map_context, (
            f"Map node KeyError should include node name and 'over' expression. "
            f"Got: {error_message}"
        )


class TestMapNodeErrorMessages:
    """Tests for helpful error messages in map nodes."""

    def test_map_error_suggests_available_keys(self) -> None:
        """Error should suggest available state keys for debugging."""
        state = {"items": [1, 2], "data": {"nested": "value"}}

        with pytest.raises(KeyError) as exc_info:
            resolve_state_expression("{typo_items}", state)

        error_message = str(exc_info.value)

        # Good error would say: "Key 'typo_items' not found. Available: items, data"
        suggests_alternatives = (
            "items" in error_message or "available" in error_message.lower()
        )

        assert (
            suggests_alternatives
        ), f"Error should suggest available keys. Got: {error_message}"
