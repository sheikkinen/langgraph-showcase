"""Tests for LangSmith tool wrappers.

Tests for the agent-facing tool wrappers in yamlgraph.tools.langsmith_tools.
"""

from unittest.mock import patch

# =============================================================================
# get_run_details_tool tests
# =============================================================================


class TestGetRunDetailsTool:
    """Tests for get_run_details_tool()."""

    def test_returns_success_with_run_details(self):
        """Returns run details with success flag."""
        from yamlgraph.tools.langsmith_tools import get_run_details_tool

        mock_details = {
            "id": "run-123",
            "name": "test_pipeline",
            "status": "success",
            "error": None,
            "start_time": "2026-01-18T10:00:00",
            "end_time": "2026-01-18T10:01:00",
            "inputs": {"topic": "AI"},
            "outputs": {"result": "done"},
            "run_type": "chain",
        }

        with patch(
            "yamlgraph.tools.langsmith_tools.get_run_details",
            return_value=mock_details,
        ):
            result = get_run_details_tool("run-123")

            assert result["success"] is True
            assert result["id"] == "run-123"
            assert result["status"] == "success"

    def test_returns_error_when_no_details(self):
        """Returns error dict when details not available."""
        from yamlgraph.tools.langsmith_tools import get_run_details_tool

        with patch(
            "yamlgraph.tools.langsmith_tools.get_run_details",
            return_value=None,
        ):
            result = get_run_details_tool("run-123")

            assert result["success"] is False
            assert "error" in result

    def test_passes_run_id_to_underlying_function(self):
        """Passes run_id parameter correctly."""
        from yamlgraph.tools.langsmith_tools import get_run_details_tool

        with patch(
            "yamlgraph.tools.langsmith_tools.get_run_details",
            return_value={"id": "test"},
        ) as mock_get:
            get_run_details_tool("specific-run-id")
            mock_get.assert_called_once_with("specific-run-id")

    def test_uses_latest_when_no_run_id(self):
        """Uses latest run when no ID provided."""
        from yamlgraph.tools.langsmith_tools import get_run_details_tool

        with patch(
            "yamlgraph.tools.langsmith_tools.get_run_details",
            return_value={"id": "latest"},
        ) as mock_get:
            get_run_details_tool()
            mock_get.assert_called_once_with(None)


# =============================================================================
# get_run_errors_tool tests
# =============================================================================


class TestGetRunErrorsTool:
    """Tests for get_run_errors_tool()."""

    def test_returns_errors_with_count(self):
        """Returns errors with count and has_errors flag."""
        from yamlgraph.tools.langsmith_tools import get_run_errors_tool

        mock_errors = [
            {"node": "generate", "error": "API failed", "run_type": "llm"},
            {"node": "analyze", "error": "Timeout", "run_type": "llm"},
        ]

        with patch(
            "yamlgraph.tools.langsmith_tools.get_run_errors",
            return_value=mock_errors,
        ):
            result = get_run_errors_tool("run-123")

            assert result["success"] is True
            assert result["error_count"] == 2
            assert result["has_errors"] is True
            assert len(result["errors"]) == 2

    def test_returns_empty_when_no_errors(self):
        """Returns empty list when no errors."""
        from yamlgraph.tools.langsmith_tools import get_run_errors_tool

        with patch(
            "yamlgraph.tools.langsmith_tools.get_run_errors",
            return_value=[],
        ):
            result = get_run_errors_tool("run-123")

            assert result["success"] is True
            assert result["error_count"] == 0
            assert result["has_errors"] is False
            assert result["errors"] == []

    def test_passes_run_id_to_underlying_function(self):
        """Passes run_id parameter correctly."""
        from yamlgraph.tools.langsmith_tools import get_run_errors_tool

        with patch(
            "yamlgraph.tools.langsmith_tools.get_run_errors",
            return_value=[],
        ) as mock_get:
            get_run_errors_tool("specific-run-id")
            mock_get.assert_called_once_with("specific-run-id")


# =============================================================================
# get_failed_runs_tool tests
# =============================================================================


class TestGetFailedRunsTool:
    """Tests for get_failed_runs_tool()."""

    def test_returns_failed_runs_with_count(self):
        """Returns failed runs with count."""
        from yamlgraph.tools.langsmith_tools import get_failed_runs_tool

        mock_runs = [
            {
                "id": "run-1",
                "name": "pipe1",
                "error": "Err1",
                "start_time": "2026-01-18T10:00:00",
            },
            {
                "id": "run-2",
                "name": "pipe2",
                "error": "Err2",
                "start_time": "2026-01-18T11:00:00",
            },
        ]

        with patch(
            "yamlgraph.tools.langsmith_tools.get_failed_runs",
            return_value=mock_runs,
        ):
            result = get_failed_runs_tool(limit=5)

            assert result["success"] is True
            assert result["failed_count"] == 2
            assert len(result["runs"]) == 2

    def test_returns_empty_when_no_failures(self):
        """Returns empty list when no failures."""
        from yamlgraph.tools.langsmith_tools import get_failed_runs_tool

        with patch(
            "yamlgraph.tools.langsmith_tools.get_failed_runs",
            return_value=[],
        ):
            result = get_failed_runs_tool()

            assert result["success"] is True
            assert result["failed_count"] == 0
            assert result["runs"] == []

    def test_passes_parameters_correctly(self):
        """Passes limit and project_name to underlying function."""
        from yamlgraph.tools.langsmith_tools import get_failed_runs_tool

        with patch(
            "yamlgraph.tools.langsmith_tools.get_failed_runs",
            return_value=[],
        ) as mock_get:
            get_failed_runs_tool(limit=5, project_name="custom-project")
            mock_get.assert_called_once_with(project_name="custom-project", limit=5)

    def test_uses_defaults_when_no_params(self):
        """Uses default limit when not provided."""
        from yamlgraph.tools.langsmith_tools import get_failed_runs_tool

        with patch(
            "yamlgraph.tools.langsmith_tools.get_failed_runs",
            return_value=[],
        ) as mock_get:
            get_failed_runs_tool()
            mock_get.assert_called_once_with(project_name=None, limit=10)
