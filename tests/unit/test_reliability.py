"""Tests for Section 1: Reliability & Error Handling.

TDD tests for on_error behaviors and fallback provider chains.
"""

from unittest.mock import MagicMock, patch

import pytest

from yamlgraph.graph_loader import GraphConfig
from yamlgraph.models import PipelineError
from yamlgraph.node_factory import create_node_function

# =============================================================================
# Test: on_error Configuration Parsing
# =============================================================================


class TestOnErrorConfigParsing:
    """Tests for parsing on_error config from YAML."""

    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_parses_on_error_from_node_config(self):
        """Node config includes on_error field."""
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "generate": {
                    "prompt": "generate",
                    "on_error": "skip",
                }
            },
            "edges": [
                {"from": "START", "to": "generate"},
                {"from": "generate", "to": "END"},
            ],
        }
        config = GraphConfig(config_dict)
        assert config.nodes["generate"]["on_error"] == "skip"

    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_parses_max_retries_from_node_config(self):
        """Node config includes max_retries field."""
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "generate": {
                    "prompt": "generate",
                    "max_retries": 5,
                }
            },
            "edges": [
                {"from": "START", "to": "generate"},
                {"from": "generate", "to": "END"},
            ],
        }
        config = GraphConfig(config_dict)
        assert config.nodes["generate"]["max_retries"] == 5

    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_parses_fallback_provider_from_node_config(self):
        """Node config includes fallback provider."""
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "generate": {
                    "prompt": "generate",
                    "on_error": "fallback",
                    "fallback": {"provider": "anthropic"},
                }
            },
            "edges": [
                {"from": "START", "to": "generate"},
                {"from": "generate", "to": "END"},
            ],
        }
        config = GraphConfig(config_dict)
        assert config.nodes["generate"]["fallback"]["provider"] == "anthropic"

    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_validates_on_error_values(self):
        """Invalid on_error value raises ValueError."""
        config_dict = {
            "version": "1.0",
            "name": "test",
            "nodes": {
                "generate": {
                    "prompt": "generate",
                    "on_error": "invalid_value",
                }
            },
            "edges": [
                {"from": "START", "to": "generate"},
                {"from": "generate", "to": "END"},
            ],
        }
        with pytest.raises(ValueError, match="on_error"):
            GraphConfig(config_dict)


# =============================================================================
# Test: on_error: skip Behavior
# =============================================================================


class TestOnErrorSkip:
    """Tests for on_error: skip behavior."""

    @patch("yamlgraph.node_factory.llm_nodes.execute_prompt")
    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_skip_returns_empty_on_failure(self, mock_execute):
        """Node with on_error: skip returns empty dict on failure."""
        mock_execute.side_effect = Exception("LLM failed")

        node_config = {
            "prompt": "generate",
            "on_error": "skip",
            "state_key": "generated",
        }
        node_fn = create_node_function("generate", node_config, {})

        result = node_fn({"topic": "test"})

        # Should NOT have error, should continue pipeline
        assert "error" not in result
        assert result.get("current_step") == "generate"

    @patch("yamlgraph.node_factory.llm_nodes.execute_prompt")
    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_skip_logs_warning(self, mock_execute):
        """Node with on_error: skip logs a warning."""
        mock_execute.side_effect = Exception("LLM failed")

        node_config = {
            "prompt": "generate",
            "on_error": "skip",
            "state_key": "generated",
        }
        node_fn = create_node_function("generate", node_config, {})

        with patch("yamlgraph.error_handlers.logger") as mock_logger:
            node_fn({"topic": "test"})
            mock_logger.warning.assert_called()


# =============================================================================
# Test: on_error: retry Behavior
# =============================================================================


class TestOnErrorRetry:
    """Tests for on_error: retry behavior."""

    @patch("yamlgraph.node_factory.llm_nodes.execute_prompt")
    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_retry_uses_node_max_retries(self, mock_execute):
        """Node uses its own max_retries, not global."""
        # Fail first 2 times, succeed on 3rd
        mock_execute.side_effect = [
            Exception("Retry 1"),
            Exception("Retry 2"),
            MagicMock(content="Success"),
        ]

        node_config = {
            "prompt": "generate",
            "on_error": "retry",
            "max_retries": 3,
            "state_key": "generated",
        }
        node_fn = create_node_function("generate", node_config, {})

        result = node_fn({"topic": "test"})

        assert mock_execute.call_count == 3
        assert "generated" in result

    @patch("yamlgraph.node_factory.llm_nodes.execute_prompt")
    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_retry_exhausted_returns_error(self, mock_execute):
        """After max_retries exhausted, returns error."""
        mock_execute.side_effect = Exception("Always fails")

        node_config = {
            "prompt": "generate",
            "on_error": "retry",
            "max_retries": 2,
            "state_key": "generated",
        }
        node_fn = create_node_function("generate", node_config, {})

        result = node_fn({"topic": "test"})

        # 1 initial attempt + 2 retries = 3 total calls
        assert mock_execute.call_count == 3
        assert "errors" in result
        assert isinstance(result["errors"][0], PipelineError)


# =============================================================================
# Test: on_error: fail Behavior
# =============================================================================


class TestOnErrorFail:
    """Tests for on_error: fail behavior."""

    @patch("yamlgraph.node_factory.llm_nodes.execute_prompt")
    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_fail_raises_exception(self, mock_execute):
        """Node with on_error: fail raises exception."""
        mock_execute.side_effect = Exception("LLM failed")

        node_config = {
            "prompt": "generate",
            "on_error": "fail",
            "state_key": "generated",
        }
        node_fn = create_node_function("generate", node_config, {})

        with pytest.raises(Exception, match="LLM failed"):
            node_fn({"topic": "test"})


# =============================================================================
# Test: on_error: fallback Behavior
# =============================================================================


class TestOnErrorFallback:
    """Tests for on_error: fallback behavior."""

    @patch("yamlgraph.node_factory.llm_nodes.execute_prompt")
    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_fallback_tries_alternate_provider(self, mock_execute):
        """Node tries fallback provider on primary failure."""
        # First call (mistral) fails, second call (anthropic) succeeds
        mock_execute.side_effect = [
            Exception("Mistral failed"),
            MagicMock(content="Anthropic success"),
        ]

        node_config = {
            "prompt": "generate",
            "provider": "mistral",
            "on_error": "fallback",
            "fallback": {"provider": "anthropic"},
            "state_key": "generated",
        }
        node_fn = create_node_function("generate", node_config, {})

        result = node_fn({"topic": "test"})

        assert mock_execute.call_count == 2
        # Second call should use anthropic
        second_call = mock_execute.call_args_list[1]
        assert second_call.kwargs.get("provider") == "anthropic"
        assert "generated" in result

    @patch("yamlgraph.node_factory.llm_nodes.execute_prompt")
    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_all_providers_fail_returns_error(self, mock_execute):
        """When all providers fail, returns error with all attempts."""
        mock_execute.side_effect = Exception("All fail")

        node_config = {
            "prompt": "generate",
            "provider": "mistral",
            "on_error": "fallback",
            "fallback": {"provider": "anthropic"},
            "state_key": "generated",
        }
        node_fn = create_node_function("generate", node_config, {})

        result = node_fn({"topic": "test"})

        assert mock_execute.call_count == 2
        assert "errors" in result
        assert isinstance(result["errors"][0], PipelineError)


# =============================================================================
# Test: Default on_error Behavior
# =============================================================================


class TestDefaultOnError:
    """Tests for default error behavior (no on_error specified)."""

    @patch("yamlgraph.node_factory.llm_nodes.execute_prompt")
    @pytest.mark.req("REQ-YG-027", "REQ-YG-029")
    def test_default_behavior_returns_error(self, mock_execute):
        """Without on_error config, current behavior returns error in state."""
        mock_execute.side_effect = Exception("LLM failed")

        node_config = {
            "prompt": "generate",
            "state_key": "generated",
            # No on_error specified
        }
        node_fn = create_node_function("generate", node_config, {})

        result = node_fn({"topic": "test"})

        # Current default behavior: return error in state (as list for consistency)
        assert "errors" in result
        assert isinstance(result["errors"][0], PipelineError)
