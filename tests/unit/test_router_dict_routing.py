"""Tests for router node dict output handling.

Bug: Router nodes only check tone/intent via getattr, so dict outputs
(e.g., when parse_json is enabled or a JSON prompt is returned) will
never match and will always fall back to default routing.
"""

from unittest.mock import patch

import pytest
from pydantic import BaseModel

from yamlgraph.node_factory import create_node_function


class TestRouterDictOutputRouting:
    """Tests for router handling of dict outputs."""

    @pytest.mark.req("REQ-YG-022")
    def test_router_routes_pydantic_model_tone(self) -> None:
        """Router should route based on Pydantic model tone attribute."""

        class RouterOutput(BaseModel):
            tone: str
            response: str

        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = RouterOutput
            mock_execute.return_value = RouterOutput(
                tone="positive", response="Great job!"
            )

            node_fn = create_node_function(
                "router",
                {
                    "type": "router",
                    "prompt": "classify",
                    "routes": {"positive": "celebrate", "negative": "console"},
                    "default_route": "neutral_handler",
                },
                {},
            )

            result = node_fn({"input": "I passed my exam!"})

            # Pydantic models should route correctly
            assert (
                result.get("_route") == "celebrate"
            ), f"Router should route to 'celebrate' for tone='positive'. Got: {result}"

    @pytest.mark.req("REQ-YG-022")
    def test_router_routes_dict_output_tone(self) -> None:
        """Router should route based on dict output tone key."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            # Dict output simulating parse_json=True
            mock_execute.return_value = {"tone": "negative", "response": "I'm sorry"}

            node_fn = create_node_function(
                "router",
                {
                    "type": "router",
                    "prompt": "classify",
                    "parse_json": True,
                    "routes": {"positive": "celebrate", "negative": "console"},
                    "default_route": "neutral_handler",
                },
                {},
            )

            result = node_fn({"input": "I failed the test"})

            # Dict outputs should route correctly
            assert result.get("_route") == "console", (
                f"Router should route to 'console' for tone='negative' dict. "
                f"Got: {result}"
            )

    @pytest.mark.req("REQ-YG-022")
    def test_router_routes_dict_output_intent(self) -> None:
        """Router should check intent key if tone is not present."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.return_value = {"intent": "question", "text": "What is this?"}

            node_fn = create_node_function(
                "router",
                {
                    "type": "router",
                    "prompt": "classify",
                    "parse_json": True,
                    "routes": {"question": "faq", "complaint": "support"},
                    "default_route": "general",
                },
                {},
            )

            result = node_fn({"input": "What is this?"})

            assert result.get("_route") == "faq", (
                f"Router should route to 'faq' for intent='question' dict. "
                f"Got: {result}"
            )

    @pytest.mark.req("REQ-YG-022")
    def test_router_falls_back_when_key_missing(self) -> None:
        """Router should fall back to default_route when tone/intent missing."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.return_value = {"category": "other", "text": "Random stuff"}

            node_fn = create_node_function(
                "router",
                {
                    "type": "router",
                    "prompt": "classify",
                    "parse_json": True,
                    "routes": {"positive": "celebrate", "negative": "console"},
                    "default_route": "neutral_handler",
                },
                {},
            )

            result = node_fn({"input": "Random text"})

            # Should fall back gracefully, not error out
            assert (
                result.get("_route") == "neutral_handler"
            ), f"Router should fall back when tone/intent missing. Got: {result}"


class TestRouterCustomRouteKey:
    """Tests for custom route_key configuration."""

    @pytest.mark.xfail(reason="route_key config not yet implemented")
    @pytest.mark.req("REQ-YG-022")
    def test_router_uses_custom_route_key(self) -> None:
        """Router should support custom route_key config for dict/model lookup."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.return_value = {"category": "urgent", "message": "Help!"}

            node_fn = create_node_function(
                "router",
                {
                    "type": "router",
                    "prompt": "classify",
                    "parse_json": True,
                    "route_key": "category",  # Custom key - NOT YET IMPLEMENTED
                    "routes": {"urgent": "escalate", "normal": "queue"},
                    "default_route": "triage",
                },
                {},
            )

            result = node_fn({"input": "Emergency!"})

            # Should use custom route_key
            assert (
                result.get("_route") == "escalate"
            ), f"Router should use custom route_key 'category'. Got: {result}"
