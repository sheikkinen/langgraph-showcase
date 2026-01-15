"""Unit tests for LangSmith utilities.

Tests for:
- share_run() - Create public share links
- read_run_shared_link() - Get existing share links
- get_client() - Client creation with env var handling
- is_tracing_enabled() - Tracing detection
"""

import os
from unittest.mock import MagicMock, patch


from showcase.utils.langsmith import (
    get_client,
    get_project_name,
    is_tracing_enabled,
    share_run,
    read_run_shared_link,
    get_latest_run_id,
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
            assert get_project_name() == "showcase-app"


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
        with patch.dict(
            os.environ,
            {"LANGCHAIN_API_KEY": "lsv2_test_key"},
            clear=True,
        ):
            with patch("langsmith.Client") as mock_client:
                result = get_client()
                mock_client.assert_called_once()
                assert result is not None

    def test_creates_client_with_langsmith_key(self):
        """Creates client with LANGSMITH_API_KEY."""
        with patch.dict(
            os.environ,
            {"LANGSMITH_API_KEY": "lsv2_test_key"},
            clear=True,
        ):
            with patch("langsmith.Client") as mock_client:
                result = get_client()
                mock_client.assert_called_once()
                assert result is not None

    def test_uses_custom_endpoint(self):
        """Uses LANGSMITH_ENDPOINT if set."""
        with patch.dict(
            os.environ,
            {
                "LANGSMITH_API_KEY": "key",
                "LANGSMITH_ENDPOINT": "https://eu.smith.langchain.com",
            },
            clear=True,
        ):
            with patch("langsmith.Client") as mock_client:
                get_client()
                mock_client.assert_called_with(
                    api_url="https://eu.smith.langchain.com",
                    api_key="key",
                )

    def test_returns_none_on_import_error(self):
        """Returns None if langsmith not installed."""
        # Verify graceful handling when Client constructor fails
        with patch.dict(os.environ, {"LANGSMITH_API_KEY": "key"}, clear=True):
            with patch("langsmith.Client", side_effect=ImportError("No module")):
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
        with patch("showcase.utils.langsmith.get_client", return_value=None):
            result = share_run("test-run-id")
            assert result is None

    def test_shares_provided_run_id(self):
        """Shares the provided run ID."""
        mock_client = MagicMock()
        mock_client.share_run.return_value = "https://smith.langchain.com/public/abc123"

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            result = share_run("my-run-id")

            mock_client.share_run.assert_called_once_with("my-run-id")
            assert result == "https://smith.langchain.com/public/abc123"

    def test_uses_latest_run_when_no_id(self):
        """Gets latest run ID when not provided."""
        mock_client = MagicMock()
        mock_client.share_run.return_value = "https://share.url"

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            with patch(
                "showcase.utils.langsmith.get_latest_run_id",
                return_value="latest-id",
            ):
                result = share_run()

                mock_client.share_run.assert_called_once_with("latest-id")
                assert result == "https://share.url"

    def test_returns_none_when_no_latest_run(self):
        """Returns None when no latest run found."""
        mock_client = MagicMock()

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            with patch(
                "showcase.utils.langsmith.get_latest_run_id",
                return_value=None,
            ):
                result = share_run()
                assert result is None

    def test_handles_exception_gracefully(self):
        """Returns None on error (logs warning to stderr)."""
        mock_client = MagicMock()
        mock_client.share_run.side_effect = Exception("API error")

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            result = share_run("test-id")
            assert result is None


# =============================================================================
# read_run_shared_link() tests
# =============================================================================


class TestReadRunSharedLink:
    """Tests for read_run_shared_link()."""

    def test_returns_none_when_no_client(self):
        """Returns None when client unavailable."""
        with patch("showcase.utils.langsmith.get_client", return_value=None):
            result = read_run_shared_link("test-run-id")
            assert result is None

    def test_returns_existing_link(self):
        """Returns existing share link."""
        mock_client = MagicMock()
        mock_client.read_run_shared_link.return_value = "https://existing.url"

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            result = read_run_shared_link("my-run-id")

            mock_client.read_run_shared_link.assert_called_once_with("my-run-id")
            assert result == "https://existing.url"

    def test_returns_none_when_not_shared(self):
        """Returns None when run not shared (exception)."""
        mock_client = MagicMock()
        mock_client.read_run_shared_link.side_effect = Exception("Not found")

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            result = read_run_shared_link("test-id")
            assert result is None


# =============================================================================
# get_latest_run_id() tests
# =============================================================================


class TestGetLatestRunId:
    """Tests for get_latest_run_id()."""

    def test_returns_none_when_no_client(self):
        """Returns None when client unavailable."""
        with patch("showcase.utils.langsmith.get_client", return_value=None):
            result = get_latest_run_id()
            assert result is None

    def test_returns_latest_run_id(self):
        """Returns ID of most recent run."""
        mock_run = MagicMock()
        mock_run.id = "abc-123"

        mock_client = MagicMock()
        mock_client.list_runs.return_value = [mock_run]

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            with patch(
                "showcase.utils.langsmith.get_project_name",
                return_value="test-project",
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

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            result = get_latest_run_id()
            assert result is None

    def test_uses_provided_project_name(self):
        """Uses provided project name."""
        mock_run = MagicMock()
        mock_run.id = "run-id"
        mock_client = MagicMock()
        mock_client.list_runs.return_value = [mock_run]

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            get_latest_run_id(project_name="custom-project")

            mock_client.list_runs.assert_called_once_with(
                project_name="custom-project", limit=1
            )

    def test_handles_exception_gracefully(self):
        """Returns None on error (logs warning to stderr)."""
        mock_client = MagicMock()
        mock_client.list_runs.side_effect = Exception("API error")

        with patch("showcase.utils.langsmith.get_client", return_value=mock_client):
            result = get_latest_run_id()
            assert result is None
