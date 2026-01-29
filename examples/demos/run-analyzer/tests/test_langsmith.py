"""Unit tests for LangSmith utilities.

Tests for:
- share_run() - Create public share links
- read_run_shared_link() - Get existing share links
- get_client() - Client creation with env var handling
- is_tracing_enabled() - Tracing detection
"""

import os
from unittest.mock import MagicMock, patch

from utils.langsmith import (
    get_client,
    get_latest_run_id,
    get_project_name,
    is_tracing_enabled,
    read_run_shared_link,
    share_run,
)

# =============================================================================
# is_tracing_enabled() tests
# =============================================================================


class TestIsTracingEnabled:
    """Tests for is_tracing_enabled()."""

    def test_enabled_with_langchain_tracing_v2_true(self):
        """LANGCHAIN_TRACING_V2=true enables tracing."""
        with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "true"}, clear=False):
            # Need to remove LANGSMITH_TRACING if set
            env = dict(os.environ)
            env.pop("LANGSMITH_TRACING", None)
            with patch.dict(os.environ, env, clear=True):
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                assert is_tracing_enabled() is True

    def test_enabled_with_langsmith_tracing_true(self):
        """LANGSMITH_TRACING=true enables tracing."""
        with patch.dict(os.environ, {"LANGSMITH_TRACING": "true"}, clear=True):
            assert is_tracing_enabled() is True

    def test_disabled_when_no_env_vars(self):
        """No tracing vars means disabled."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_tracing_enabled() is False

    def test_disabled_with_false_value(self):
        """Explicit false value disables tracing."""
        with patch.dict(os.environ, {"LANGCHAIN_TRACING_V2": "false"}, clear=True):
            assert is_tracing_enabled() is False

    def test_case_insensitive(self):
        """TRUE, True, true all work."""
        with patch.dict(os.environ, {"LANGSMITH_TRACING": "TRUE"}, clear=True):
            assert is_tracing_enabled() is True


# =============================================================================
# get_project_name() tests
# =============================================================================


class TestGetProjectName:
    """Tests for get_project_name()."""

    def test_langchain_project(self):
        """Returns LANGCHAIN_PROJECT when set."""
        with patch.dict(os.environ, {"LANGCHAIN_PROJECT": "my-project"}, clear=True):
            assert get_project_name() == "my-project"

    def test_langsmith_project(self):
        """Returns LANGSMITH_PROJECT when set."""
        with patch.dict(os.environ, {"LANGSMITH_PROJECT": "other-project"}, clear=True):
            assert get_project_name() == "other-project"

    def test_langchain_takes_precedence(self):
        """LANGCHAIN_PROJECT takes precedence over LANGSMITH_PROJECT."""
        with patch.dict(
            os.environ,
            {"LANGCHAIN_PROJECT": "first", "LANGSMITH_PROJECT": "second"},
            clear=True,
        ):
            assert get_project_name() == "first"

    def test_default_value(self):
        """Returns default when no env vars."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_project_name() == "yamlgraph"


# =============================================================================
# get_client() tests
# =============================================================================


class TestGetClient:
    """Tests for get_client()."""

    def test_returns_none_without_api_key(self):
        """No API key means no client."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_client() is None

    def test_creates_client_with_langchain_key(self):
        """Creates client with LANGCHAIN_API_KEY."""
        with (
            patch.dict(
                os.environ,
                {"LANGCHAIN_API_KEY": "lsv2_test_key"},
                clear=True,
            ),
            patch("langsmith.Client") as mock_client,
        ):
            result = get_client()
            mock_client.assert_called_once()
            assert result is not None

    def test_creates_client_with_langsmith_key(self):
        """Creates client with LANGSMITH_API_KEY."""
        with (
            patch.dict(
                os.environ,
                {"LANGSMITH_API_KEY": "lsv2_test_key"},
                clear=True,
            ),
            patch("langsmith.Client") as mock_client,
        ):
            result = get_client()
            mock_client.assert_called_once()
            assert result is not None

    def test_uses_custom_endpoint(self):
        """Uses LANGSMITH_ENDPOINT if set."""
        with (
            patch.dict(
                os.environ,
                {
                    "LANGSMITH_API_KEY": "key",
                    "LANGSMITH_ENDPOINT": "https://eu.smith.langchain.com",
                },
                clear=True,
            ),
            patch("langsmith.Client") as mock_client,
        ):
            get_client()
            mock_client.assert_called_with(
                api_url="https://eu.smith.langchain.com",
                api_key="key",
            )

    def test_returns_none_on_import_error(self):
        """Returns None if langsmith not installed."""
        # Verify graceful handling when Client constructor fails
        with (
            patch.dict(os.environ, {"LANGSMITH_API_KEY": "key"}, clear=True),
            patch("langsmith.Client", side_effect=ImportError("No module")),
        ):
            # Should catch ImportError and return None
            result = get_client()
            assert result is None


# =============================================================================
# share_run() tests
# =============================================================================


class TestShareRun:
    """Tests for share_run()."""

    def test_returns_none_when_no_client(self):
        """Returns None when client unavailable."""
        with patch("utils.langsmith.get_client", return_value=None):
            result = share_run("test-run-id")
            assert result is None

    def test_shares_provided_run_id(self):
        """Shares the provided run ID."""
        mock_client = MagicMock()
        mock_client.share_run.return_value = "https://smith.langchain.com/public/abc123"

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = share_run("my-run-id")

            mock_client.share_run.assert_called_once_with("my-run-id")
            assert result == "https://smith.langchain.com/public/abc123"

    def test_uses_latest_run_when_no_id(self):
        """Gets latest run ID when not provided."""
        mock_client = MagicMock()
        mock_client.share_run.return_value = "https://share.url"

        with (
            patch("utils.langsmith.get_client", return_value=mock_client),
            patch(
                "utils.langsmith.get_latest_run_id",
                return_value="latest-id",
            ),
        ):
            result = share_run()

            mock_client.share_run.assert_called_once_with("latest-id")
            assert result == "https://share.url"

    def test_returns_none_when_no_latest_run(self):
        """Returns None when no latest run found."""
        mock_client = MagicMock()

        with (
            patch("utils.langsmith.get_client", return_value=mock_client),
            patch(
                "utils.langsmith.get_latest_run_id",
                return_value=None,
            ),
        ):
            result = share_run()
            assert result is None

    def test_handles_exception_gracefully(self):
        """Returns None on error (logs warning to stderr)."""
        mock_client = MagicMock()
        mock_client.share_run.side_effect = Exception("API error")

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = share_run("test-id")
            assert result is None


# =============================================================================
# read_run_shared_link() tests
# =============================================================================


class TestReadRunSharedLink:
    """Tests for read_run_shared_link()."""

    def test_returns_none_when_no_client(self):
        """Returns None when client unavailable."""
        with patch("utils.langsmith.get_client", return_value=None):
            result = read_run_shared_link("test-run-id")
            assert result is None

    def test_returns_existing_link(self):
        """Returns existing share link."""
        mock_client = MagicMock()
        mock_client.read_run_shared_link.return_value = "https://existing.url"

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = read_run_shared_link("my-run-id")

            mock_client.read_run_shared_link.assert_called_once_with("my-run-id")
            assert result == "https://existing.url"

    def test_returns_none_when_not_shared(self):
        """Returns None when run not shared (exception)."""
        mock_client = MagicMock()
        mock_client.read_run_shared_link.side_effect = Exception("Not found")

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = read_run_shared_link("test-id")
            assert result is None


# =============================================================================
# get_latest_run_id() tests
# =============================================================================


class TestGetLatestRunId:
    """Tests for get_latest_run_id()."""

    def test_returns_none_when_no_client(self):
        """Returns None when client unavailable."""
        with patch("utils.langsmith.get_client", return_value=None):
            result = get_latest_run_id()
            assert result is None

    def test_returns_latest_run_id(self):
        """Returns ID of most recent run."""
        mock_run = MagicMock()
        mock_run.id = "abc-123"

        mock_client = MagicMock()
        mock_client.list_runs.return_value = [mock_run]

        with (
            patch("utils.langsmith.get_client", return_value=mock_client),
            patch(
                "utils.langsmith.get_project_name",
                return_value="test-project",
            ),
        ):
            result = get_latest_run_id()

            mock_client.list_runs.assert_called_once_with(
                project_name="test-project", limit=1
            )
            assert result == "abc-123"

    def test_returns_none_when_no_runs(self):
        """Returns None when no runs found."""
        mock_client = MagicMock()
        mock_client.list_runs.return_value = []

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = get_latest_run_id()
            assert result is None

    def test_uses_provided_project_name(self):
        """Uses provided project name."""
        mock_run = MagicMock()
        mock_run.id = "run-id"
        mock_client = MagicMock()
        mock_client.list_runs.return_value = [mock_run]

        with patch("utils.langsmith.get_client", return_value=mock_client):
            get_latest_run_id(project_name="custom-project")

            mock_client.list_runs.assert_called_once_with(
                project_name="custom-project", limit=1
            )

    def test_handles_exception_gracefully(self):
        """Returns None on error (logs warning to stderr)."""
        mock_client = MagicMock()
        mock_client.list_runs.side_effect = Exception("API error")

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = get_latest_run_id()
            assert result is None


# =============================================================================
# get_run_details() tests
# =============================================================================


class TestGetRunDetails:
    """Tests for get_run_details()."""

    def test_returns_none_when_no_client(self):
        """Returns None when client unavailable."""
        from utils.langsmith import get_run_details

        with patch("utils.langsmith.get_client", return_value=None):
            result = get_run_details("test-run-id")
            assert result is None

    def test_returns_none_when_no_run_id_and_no_latest(self):
        """Returns None when no run ID provided and no latest run."""
        from utils.langsmith import get_run_details

        mock_client = MagicMock()
        with (
            patch("utils.langsmith.get_client", return_value=mock_client),
            patch("utils.langsmith.get_latest_run_id", return_value=None),
        ):
            result = get_run_details()
            assert result is None

    def test_returns_run_details(self):
        """Returns detailed run information."""
        from datetime import datetime

        from utils.langsmith import get_run_details

        mock_run = MagicMock()
        mock_run.id = "run-123"
        mock_run.name = "test_pipeline"
        mock_run.status = "success"
        mock_run.error = None
        mock_run.start_time = datetime(2026, 1, 18, 10, 0, 0)
        mock_run.end_time = datetime(2026, 1, 18, 10, 1, 0)
        mock_run.inputs = {"topic": "AI"}
        mock_run.outputs = {"result": "done"}
        mock_run.run_type = "chain"

        mock_client = MagicMock()
        mock_client.read_run.return_value = mock_run

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = get_run_details("run-123")

            assert result["id"] == "run-123"
            assert result["name"] == "test_pipeline"
            assert result["status"] == "success"
            assert result["error"] is None
            assert result["inputs"] == {"topic": "AI"}
            assert result["outputs"] == {"result": "done"}
            assert result["run_type"] == "chain"

    def test_uses_latest_run_when_no_id(self):
        """Uses latest run ID when not provided."""
        from utils.langsmith import get_run_details

        mock_run = MagicMock()
        mock_run.id = "latest-run"
        mock_run.name = "latest"
        mock_run.status = "success"
        mock_run.error = None
        mock_run.start_time = None
        mock_run.end_time = None
        mock_run.inputs = {}
        mock_run.outputs = {}
        mock_run.run_type = "chain"

        mock_client = MagicMock()
        mock_client.read_run.return_value = mock_run

        with (
            patch("utils.langsmith.get_client", return_value=mock_client),
            patch(
                "utils.langsmith.get_latest_run_id",
                return_value="latest-run",
            ),
        ):
            result = get_run_details()

            mock_client.read_run.assert_called_once_with("latest-run")
            assert result["id"] == "latest-run"

    def test_handles_exception_gracefully(self):
        """Returns None on error."""
        from utils.langsmith import get_run_details

        mock_client = MagicMock()
        mock_client.read_run.side_effect = Exception("API error")

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = get_run_details("test-id")
            assert result is None


# =============================================================================
# get_run_errors() tests
# =============================================================================


class TestGetRunErrors:
    """Tests for get_run_errors()."""

    def test_returns_empty_list_when_no_client(self):
        """Returns empty list when client unavailable."""
        from utils.langsmith import get_run_errors

        with patch("utils.langsmith.get_client", return_value=None):
            result = get_run_errors("test-run-id")
            assert result == []

    def test_returns_empty_list_when_no_run_id(self):
        """Returns empty list when no run ID and no latest."""
        from utils.langsmith import get_run_errors

        mock_client = MagicMock()
        with (
            patch("utils.langsmith.get_client", return_value=mock_client),
            patch("utils.langsmith.get_latest_run_id", return_value=None),
        ):
            result = get_run_errors()
            assert result == []

    def test_returns_parent_run_error(self):
        """Returns error from parent run."""
        from utils.langsmith import get_run_errors

        mock_run = MagicMock()
        mock_run.name = "parent_node"
        mock_run.error = "Parent failed"
        mock_run.run_type = "chain"

        mock_client = MagicMock()
        mock_client.read_run.return_value = mock_run
        mock_client.list_runs.return_value = []

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = get_run_errors("run-123")

            assert len(result) == 1
            assert result[0]["node"] == "parent_node"
            assert result[0]["error"] == "Parent failed"

    def test_returns_child_run_errors(self):
        """Returns errors from child runs."""
        from utils.langsmith import get_run_errors

        mock_parent = MagicMock()
        mock_parent.error = None

        mock_child1 = MagicMock()
        mock_child1.name = "generate"
        mock_child1.error = "Generate failed"
        mock_child1.run_type = "llm"

        mock_child2 = MagicMock()
        mock_child2.name = "analyze"
        mock_child2.error = "Analyze failed"
        mock_child2.run_type = "llm"

        mock_client = MagicMock()
        mock_client.read_run.return_value = mock_parent
        mock_client.list_runs.return_value = [mock_child1, mock_child2]

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = get_run_errors("run-123")

            assert len(result) == 2
            assert result[0]["node"] == "generate"
            assert result[1]["node"] == "analyze"

    def test_handles_exception_gracefully(self):
        """Returns empty list on error."""
        from utils.langsmith import get_run_errors

        mock_client = MagicMock()
        mock_client.read_run.side_effect = Exception("API error")

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = get_run_errors("test-id")
            assert result == []


# =============================================================================
# get_failed_runs() tests
# =============================================================================


class TestGetFailedRuns:
    """Tests for get_failed_runs()."""

    def test_returns_empty_list_when_no_client(self):
        """Returns empty list when client unavailable."""
        from utils.langsmith import get_failed_runs

        with patch("utils.langsmith.get_client", return_value=None):
            result = get_failed_runs()
            assert result == []

    def test_returns_failed_runs(self):
        """Returns list of failed runs."""
        from datetime import datetime

        from utils.langsmith import get_failed_runs

        mock_run1 = MagicMock()
        mock_run1.id = "run-1"
        mock_run1.name = "pipeline_1"
        mock_run1.error = "Error 1"
        mock_run1.start_time = datetime(2026, 1, 18, 10, 0, 0)

        mock_run2 = MagicMock()
        mock_run2.id = "run-2"
        mock_run2.name = "pipeline_2"
        mock_run2.error = "Error 2"
        mock_run2.start_time = datetime(2026, 1, 18, 11, 0, 0)

        mock_client = MagicMock()
        mock_client.list_runs.return_value = [mock_run1, mock_run2]

        with (
            patch("utils.langsmith.get_client", return_value=mock_client),
            patch(
                "utils.langsmith.get_project_name",
                return_value="test-project",
            ),
        ):
            result = get_failed_runs(limit=5)

            mock_client.list_runs.assert_called_once_with(
                project_name="test-project",
                error=True,
                limit=5,
            )
            assert len(result) == 2
            assert result[0]["id"] == "run-1"
            assert result[0]["error"] == "Error 1"

    def test_uses_provided_project_name(self):
        """Uses provided project name."""
        from utils.langsmith import get_failed_runs

        mock_client = MagicMock()
        mock_client.list_runs.return_value = []

        with patch("utils.langsmith.get_client", return_value=mock_client):
            get_failed_runs(project_name="custom-project", limit=3)

            mock_client.list_runs.assert_called_once_with(
                project_name="custom-project",
                error=True,
                limit=3,
            )

    def test_handles_exception_gracefully(self):
        """Returns empty list on error."""
        from utils.langsmith import get_failed_runs

        mock_client = MagicMock()
        mock_client.list_runs.side_effect = Exception("API error")

        with patch("utils.langsmith.get_client", return_value=mock_client):
            result = get_failed_runs()
            assert result == []
