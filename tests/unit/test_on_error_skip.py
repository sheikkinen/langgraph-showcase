"""Tests for on_error: skip behavior.

Bug: on_error: skip for LLM nodes drops the error and does not clear or
update state_key, which can leave stale outputs in place and make
failures invisible in downstream logic.
"""

from unittest.mock import patch

from yamlgraph.node_factory import create_node_function


class TestOnErrorSkipBehavior:
    """Tests for on_error: skip handling."""

    def test_skip_leaves_stale_state_key(self) -> None:
        """on_error: skip should clear or mark state_key to prevent stale data."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.side_effect = Exception("LLM API error")

            node_fn = create_node_function(
                "analyzer",
                {
                    "type": "llm",
                    "prompt": "analyze",
                    "on_error": "skip",
                    "state_key": "analysis_result",
                    "skip_if_exists": False,  # Disable to ensure error path is tested
                },
                {},
            )

            # State has stale data from previous run
            state = {
                "input": "new data",
                "analysis_result": "OLD STALE RESULT",  # From previous successful run
            }

            result = node_fn(state)

            # Result should set state_key to prevent downstream using stale data
            has_state_key_update = "analysis_result" in result

            assert has_state_key_update, (
                f"on_error: skip should explicitly set state_key in result to "
                f"prevent downstream nodes from using stale data. "
                f"Got result keys: {list(result.keys())}"
            )

    def test_skip_provides_error_indicator(self) -> None:
        """on_error: skip should provide some indicator that node was skipped."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.side_effect = Exception("Rate limit exceeded")

            node_fn = create_node_function(
                "processor",
                {
                    "type": "llm",
                    "prompt": "process",
                    "on_error": "skip",
                },
                {},
            )

            result = node_fn({"input": "test"})

            # Should have some indication that node was skipped due to error
            has_skip_indicator = (
                result.get("_skipped") is True
                or result.get("_skip_reason") is not None
                or "processor" in result.get("_skipped_nodes", [])
            )

            assert has_skip_indicator, (
                f"on_error: skip should provide indicator that node was skipped. "
                f"Got: {result}"
            )

    def test_skip_clears_state_key_to_none(self) -> None:
        """on_error: skip should set state_key to None to prevent stale data."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.side_effect = Exception("Connection timeout")

            node_fn = create_node_function(
                "summarizer",
                {
                    "type": "llm",
                    "prompt": "summarize",
                    "on_error": "skip",
                    "state_key": "summary",
                },
                {},
            )

            state = {
                "input": "new document",
                "summary": "Previous summary that is now stale",
            }

            result = node_fn(state)

            # state_key should be set to None to prevent stale data
            assert result.get("summary") is None, (
                f"on_error: skip should set state_key to None. "
                f"Got summary={result.get('summary')}"
            )


class TestOnErrorSkipWithSkipIfExists:
    """Tests for on_error: skip interaction with skip_if_exists."""

    def test_skip_error_distinguishable_from_skip_if_exists(self) -> None:
        """Skipped-due-to-error should be distinguishable from skip_if_exists."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.side_effect = Exception("API error")

            node_fn = create_node_function(
                "generator",
                {
                    "type": "llm",
                    "prompt": "generate",
                    "on_error": "skip",
                    "skip_if_exists": True,
                    "state_key": "output",
                },
                {},
            )

            # No existing output - node should attempt execution
            result = node_fn({"input": "test"})

            # Result should indicate this was an error-skip, not a skip_if_exists
            is_error_skip = (
                result.get("_skip_reason") == "error"
                or result.get("_error_skipped") is True
            )

            assert is_error_skip or result.get("output") is None, (
                "Error-skip should be distinguishable from skip_if_exists. "
                f"Got: {result}"
            )


class TestOnErrorSkipLogging:
    """Tests for on_error: skip logging behavior."""

    def test_skip_logs_error_details(self) -> None:
        """on_error: skip should log error details for debugging."""

        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
            patch(
                "yamlgraph.error_handlers.logger"
            ) as mock_logger,  # Error handlers log
        ):
            mock_get_model.return_value = None
            error_msg = "Specific API error: rate limit"
            mock_execute.side_effect = Exception(error_msg)

            node_fn = create_node_function(
                "test_node",
                {
                    "type": "llm",
                    "prompt": "test",
                    "on_error": "skip",
                },
                {},
            )

            node_fn({"input": "test"})

            # Verify error was logged (warning or info level)
            log_calls = mock_logger.method_calls

            # At minimum, the skip should be logged
            assert len(log_calls) > 0, "on_error: skip should log the skip event"
