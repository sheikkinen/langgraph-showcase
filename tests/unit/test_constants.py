"""Tests for yamlgraph.constants module.

Covers:
- NodeType constants
- ErrorHandler strategies
- EdgeType constants
- SpecialNodes constants
"""

import pytest

from yamlgraph.constants import EdgeType, ErrorHandler, NodeType, SpecialNodes


class TestNodeType:
    """Tests for NodeType enum."""

    @pytest.mark.req("REQ-YG-043")
    def test_all_node_types_defined(self) -> None:
        """Test all expected node types exist."""
        expected = {
            "llm",
            "router",
            "tool",
            "agent",
            "python",
            "map",
            "tool_call",
            "interrupt",
            "subgraph",
            "passthrough",
        }
        actual = {nt.value for nt in NodeType}
        assert actual == expected

    @pytest.mark.req("REQ-YG-043")
    def test_node_type_is_str_enum(self) -> None:
        """Test NodeType values are strings."""
        assert NodeType.LLM == "llm"
        assert str(NodeType.ROUTER) == "router"

    @pytest.mark.req("REQ-YG-043")
    def test_requires_prompt_llm(self) -> None:
        """Test LLM node requires prompt."""
        assert NodeType.requires_prompt(NodeType.LLM) is True

    @pytest.mark.req("REQ-YG-043")
    def test_requires_prompt_router(self) -> None:
        """Test router node requires prompt."""
        assert NodeType.requires_prompt(NodeType.ROUTER) is True

    @pytest.mark.req("REQ-YG-043")
    def test_requires_prompt_python(self) -> None:
        """Test python node does not require prompt."""
        assert NodeType.requires_prompt(NodeType.PYTHON) is False

    @pytest.mark.req("REQ-YG-043")
    def test_requires_prompt_map(self) -> None:
        """Test map node does not require prompt."""
        assert NodeType.requires_prompt(NodeType.MAP) is False

    @pytest.mark.req("REQ-YG-043")
    def test_requires_prompt_tool_call(self) -> None:
        """Test tool_call node does not require prompt."""
        assert NodeType.requires_prompt(NodeType.TOOL_CALL) is False


class TestErrorHandler:
    """Tests for ErrorHandler enum."""

    @pytest.mark.req("REQ-YG-043")
    def test_all_error_handlers_defined(self) -> None:
        """Test all expected error handlers exist."""
        expected = {"skip", "retry", "fail", "fallback"}
        actual = {eh.value for eh in ErrorHandler}
        assert actual == expected

    @pytest.mark.req("REQ-YG-043")
    def test_error_handler_is_str_enum(self) -> None:
        """Test ErrorHandler values are strings."""
        assert ErrorHandler.SKIP == "skip"
        assert ErrorHandler.RETRY == "retry"
        assert ErrorHandler.FAIL == "fail"
        assert ErrorHandler.FALLBACK == "fallback"

    @pytest.mark.req("REQ-YG-043")
    def test_all_values_returns_set(self) -> None:
        """Test all_values class method returns complete set."""
        values = ErrorHandler.all_values()
        assert isinstance(values, set)
        assert values == {"skip", "retry", "fail", "fallback"}

    @pytest.mark.req("REQ-YG-043")
    def test_all_values_for_validation(self) -> None:
        """Test all_values can be used for validation."""
        valid_handler = "retry"
        invalid_handler = "ignore"

        assert valid_handler in ErrorHandler.all_values()
        assert invalid_handler not in ErrorHandler.all_values()


class TestEdgeType:
    """Tests for EdgeType enum."""

    @pytest.mark.req("REQ-YG-043")
    def test_all_edge_types_defined(self) -> None:
        """Test all expected edge types exist."""
        expected = {"simple", "conditional"}
        actual = {et.value for et in EdgeType}
        assert actual == expected

    @pytest.mark.req("REQ-YG-043")
    def test_edge_type_is_str_enum(self) -> None:
        """Test EdgeType values are strings."""
        assert EdgeType.SIMPLE == "simple"
        assert EdgeType.CONDITIONAL == "conditional"


class TestSpecialNodes:
    """Tests for SpecialNodes enum."""

    @pytest.mark.req("REQ-YG-043")
    def test_start_node(self) -> None:
        """Test START special node value."""
        assert SpecialNodes.START == "__start__"

    @pytest.mark.req("REQ-YG-043")
    def test_end_node(self) -> None:
        """Test END special node value."""
        assert SpecialNodes.END == "__end__"

    @pytest.mark.req("REQ-YG-043")
    def test_special_nodes_are_strings(self) -> None:
        """Test special node values are strings."""
        assert isinstance(SpecialNodes.START.value, str)
        assert isinstance(SpecialNodes.END.value, str)


class TestModuleExports:
    """Tests for module __all__ exports."""

    @pytest.mark.req("REQ-YG-043")
    def test_all_exports_available(self) -> None:
        """Test all exports are importable."""
        from yamlgraph.constants import (
            EdgeType,
            ErrorHandler,
            NodeType,
            SpecialNodes,
        )

        # All should be non-None
        assert NodeType is not None
        assert ErrorHandler is not None
        assert EdgeType is not None
        assert SpecialNodes is not None
