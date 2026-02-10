"""FR-026: Chaplain audit fixes — TDD tests.

Four findings from Chaplain code audit:
1. HIGH: wrap_for_reducer crashes on non-dict python return
2. MEDIUM: LLM SKIP drops error details
3. MEDIUM: tool/python nodes ignore retry/fallback (linter E011)
4. LOW: prompts_relative guard too narrow (warning)
"""

import contextlib
from pathlib import Path
from unittest.mock import patch

import pytest

from yamlgraph.linter.checks import LintIssue, check_error_handling
from yamlgraph.map_compiler import wrap_for_reducer
from yamlgraph.models import PipelineError
from yamlgraph.node_factory import create_node_function

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "linter"


def issue_codes(issues: list[LintIssue]) -> list[str]:
    """Extract issue codes from a list of LintIssue."""
    return [i.code for i in issues]


# ===========================================================================
# Finding 1 — HIGH: wrap_for_reducer handles non-dict returns
# ===========================================================================


class TestWrapForReducerNonDict:
    """wrap_for_reducer must handle non-dict returns from python sub-nodes."""

    @pytest.mark.req("REQ-YG-041")
    def test_string_return_does_not_crash(self):
        """Python sub-node returning string should not raise AttributeError."""

        def string_node(state: dict) -> str:
            return "hello world"

        wrapped = wrap_for_reducer(string_node, "results", "output")
        result = wrapped({"_map_index": 0})

        # Should not crash, should collect the value
        assert "results" in result
        assert len(result["results"]) == 1

    @pytest.mark.req("REQ-YG-041")
    def test_int_return_does_not_crash(self):
        """Python sub-node returning int should not raise AttributeError."""

        def int_node(state: dict) -> int:
            return 42

        wrapped = wrap_for_reducer(int_node, "results", "output")
        result = wrapped({"_map_index": 0})

        assert "results" in result
        assert result["results"][0]["value"] == 42

    @pytest.mark.req("REQ-YG-041")
    def test_string_return_wraps_with_map_index(self):
        """Non-dict return gets wrapped with _map_index and value key."""

        def string_node(state: dict) -> str:
            return "processed"

        wrapped = wrap_for_reducer(string_node, "results", "output")
        result = wrapped({"_map_index": 3})

        item = result["results"][0]
        assert item["_map_index"] == 3
        assert item["value"] == "processed"

    @pytest.mark.req("REQ-YG-041")
    def test_dict_return_still_works(self):
        """Dict return should continue to work as before."""

        def dict_node(state: dict) -> dict:
            return {"output": "some result", "meta": "data"}

        wrapped = wrap_for_reducer(dict_node, "results", "output")
        result = wrapped({"_map_index": 0})

        assert "results" in result
        item = result["results"][0]
        assert item["_map_index"] == 0
        # state_key "output" is extracted → "some result" (non-dict, wrapped as value)
        assert item["value"] == "some result"

    @pytest.mark.req("REQ-YG-041")
    def test_list_return_wraps_as_value(self):
        """List return should be wrapped with value key."""

        def list_node(state: dict) -> list:
            return [1, 2, 3]

        wrapped = wrap_for_reducer(list_node, "results", "output")
        result = wrapped({"_map_index": 1})

        item = result["results"][0]
        assert item["_map_index"] == 1
        assert item["value"] == [1, 2, 3]


# ===========================================================================
# Finding 2 — MEDIUM: LLM SKIP records PipelineError in errors list
# ===========================================================================


class TestLLMSkipRecordsError:
    """LLM on_error: skip should record PipelineError like tool/python nodes."""

    @pytest.mark.req("REQ-YG-027")
    def test_llm_skip_has_errors_list(self):
        """LLM on_error: skip should include 'errors' list with PipelineError."""
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
                    "state_key": "analysis",
                    "skip_if_exists": False,
                },
                {},
            )

            result = node_fn({"input": "test"})

            assert (
                "errors" in result
            ), f"LLM skip should include 'errors' key. Got keys: {list(result.keys())}"
            assert len(result["errors"]) >= 1
            error = result["errors"][0]
            assert isinstance(error, PipelineError)

    @pytest.mark.req("REQ-YG-027")
    def test_llm_skip_error_has_node_name(self):
        """PipelineError in LLM skip should reference the node name."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.side_effect = ValueError("Bad request")

            node_fn = create_node_function(
                "my_node",
                {
                    "type": "llm",
                    "prompt": "test",
                    "on_error": "skip",
                    "skip_if_exists": False,
                },
                {},
            )

            result = node_fn({"input": "test"})

            assert "errors" in result
            assert result["errors"][0].node == "my_node"

    @pytest.mark.req("REQ-YG-027")
    def test_llm_skip_error_has_message(self):
        """PipelineError in LLM skip should contain the error message."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.side_effect = RuntimeError("Connection timeout")

            node_fn = create_node_function(
                "timeout_node",
                {
                    "type": "llm",
                    "prompt": "test",
                    "on_error": "skip",
                    "skip_if_exists": False,
                },
                {},
            )

            result = node_fn({"input": "test"})

            assert "errors" in result
            assert "Connection timeout" in result["errors"][0].message

    @pytest.mark.req("REQ-YG-027")
    def test_llm_skip_still_clears_state_key(self):
        """LLM skip should still set state_key to None (existing behavior)."""
        with (
            patch("yamlgraph.node_factory.llm_nodes.execute_prompt") as mock_execute,
            patch(
                "yamlgraph.node_factory.llm_nodes.get_output_model_for_node"
            ) as mock_get_model,
        ):
            mock_get_model.return_value = None
            mock_execute.side_effect = Exception("Error")

            node_fn = create_node_function(
                "node",
                {
                    "type": "llm",
                    "prompt": "test",
                    "on_error": "skip",
                    "state_key": "output",
                    "skip_if_exists": False,
                },
                {},
            )

            result = node_fn({"output": "stale"})

            assert result.get("output") is None
            assert result.get("_skipped") is True


# ===========================================================================
# Finding 3 — MEDIUM: Linter E011 for retry/fallback on tool/python nodes
# ===========================================================================


class TestLinterE011RetryFallbackToolPython:
    """Linter should warn when tool/python nodes use on_error: retry/fallback."""

    @pytest.mark.req("REQ-YG-054")
    def test_retry_on_tool_node_warns(self):
        """on_error: retry on type: tool should produce E011."""
        issues = check_error_handling(FIXTURES / "retry_tool_fail.yaml")
        codes = issue_codes(issues)
        assert "E011" in codes

    @pytest.mark.req("REQ-YG-054")
    def test_retry_on_python_node_warns(self):
        """on_error: retry on type: python should produce E011."""
        issues = check_error_handling(FIXTURES / "retry_tool_fail.yaml")
        codes = issue_codes(issues)
        # The fixture has both tool and python with retry
        assert codes.count("E011") >= 2

    @pytest.mark.req("REQ-YG-054")
    def test_fallback_on_tool_node_warns(self):
        """on_error: fallback on type: tool should produce E011."""
        issues = check_error_handling(FIXTURES / "retry_tool_fail.yaml")
        codes = issue_codes(issues)
        # Fixture includes fallback on tool too
        assert "E011" in codes

    @pytest.mark.req("REQ-YG-054")
    def test_retry_on_llm_does_not_warn(self):
        """on_error: retry on type: llm should NOT produce E011."""
        issues = check_error_handling(FIXTURES / "retry_tool_pass.yaml")
        codes = issue_codes(issues)
        assert "E011" not in codes

    @pytest.mark.req("REQ-YG-054")
    def test_skip_on_tool_does_not_warn(self):
        """on_error: skip on type: tool is valid — no E011."""
        issues = check_error_handling(FIXTURES / "retry_tool_pass.yaml")
        codes = issue_codes(issues)
        assert "E011" not in codes

    @pytest.mark.req("REQ-YG-054")
    def test_fail_on_python_does_not_warn(self):
        """on_error: fail on type: python is valid — no E011."""
        issues = check_error_handling(FIXTURES / "retry_tool_pass.yaml")
        codes = issue_codes(issues)
        assert "E011" not in codes


# ===========================================================================
# Finding 4 — LOW: prompts_relative warning on graph_path=None + prompts_dir
# ===========================================================================


class TestPromptsRelativeWarning:
    """prompts_relative=True with graph_path=None + prompts_dir should warn."""

    @pytest.mark.req("REQ-YG-012")
    def test_warns_when_graph_path_none_but_prompts_dir_set(self):
        """Should log warning when prompts_relative=True, graph_path=None, prompts_dir set."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        with patch("yamlgraph.utils.prompts.logger") as mock_logger:
            # This should not raise (prompts_dir provides a fallback)
            # but should log a warning
            with contextlib.suppress(FileNotFoundError):
                resolve_prompt_path(
                    "nonexistent_prompt",
                    prompts_relative=True,
                    graph_path=None,
                    prompts_dir=Path("/tmp/prompts"),
                )

            # Should have logged a warning about prompts_relative without graph_path
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            has_warning = any(
                "prompts_relative" in str(c) or "graph_path" in str(c)
                for c in warning_calls
            )
            assert has_warning, (
                f"Should warn about prompts_relative=True without graph_path. "
                f"Warning calls: {warning_calls}"
            )

    @pytest.mark.req("REQ-YG-012")
    def test_no_warning_when_both_set(self):
        """No warning when both graph_path and prompts_dir are set."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        with patch("yamlgraph.utils.prompts.logger") as mock_logger:
            with contextlib.suppress(FileNotFoundError):
                resolve_prompt_path(
                    "nonexistent_prompt",
                    prompts_relative=True,
                    graph_path=Path("/tmp/graph.yaml"),
                    prompts_dir=Path("prompts"),
                )

            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            has_prompts_relative_warning = any(
                "prompts_relative" in str(c) for c in warning_calls
            )
            assert not has_prompts_relative_warning

    @pytest.mark.req("REQ-YG-012")
    def test_still_raises_when_both_none(self):
        """prompts_relative=True with both graph_path and prompts_dir None still raises."""
        from yamlgraph.utils.prompts import resolve_prompt_path

        with pytest.raises(ValueError, match="graph_path required"):
            resolve_prompt_path(
                "any_prompt",
                prompts_relative=True,
                graph_path=None,
                prompts_dir=None,
            )
