"""Tests for LangSmith tracing utilities (FR-022).

TDD tests for `yamlgraph/utils/tracing.py`.
"""

from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# is_tracing_enabled
# =============================================================================


class TestIsTracingEnabled:
    """Tests for tracing auto-detection via langsmith SDK."""

    @pytest.mark.req("REQ-YG-047")
    @patch("langsmith.utils.tracing_is_enabled", return_value=True)
    def test_enabled_when_sdk_says_true(self, _mock):
        """Should return True when langsmith SDK reports tracing enabled."""
        from yamlgraph.utils.tracing import is_tracing_enabled

        assert is_tracing_enabled() is True

    @pytest.mark.req("REQ-YG-047")
    @patch("langsmith.utils.tracing_is_enabled", return_value=False)
    def test_disabled_when_sdk_says_false(self, _mock):
        """Should return False when langsmith SDK reports tracing disabled."""
        from yamlgraph.utils.tracing import is_tracing_enabled

        assert is_tracing_enabled() is False

    @pytest.mark.req("REQ-YG-047")
    @patch("langsmith.utils.tracing_is_enabled", side_effect=Exception("import err"))
    def test_disabled_on_sdk_error(self, _mock):
        """Should return False gracefully when langsmith SDK raises."""
        from yamlgraph.utils.tracing import is_tracing_enabled

        assert is_tracing_enabled() is False


# =============================================================================
# create_tracer
# =============================================================================


class TestCreateTracer:
    """Tests for tracer factory."""

    @pytest.mark.req("REQ-YG-047")
    @patch("yamlgraph.utils.tracing.is_tracing_enabled", return_value=False)
    def test_returns_none_when_tracing_disabled(self, _mock):
        """Should return None when tracing is not enabled."""
        from yamlgraph.utils.tracing import create_tracer

        assert create_tracer() is None

    @pytest.mark.req("REQ-YG-047")
    @patch("yamlgraph.utils.tracing.is_tracing_enabled", return_value=True)
    @patch("langchain_core.tracers.LangChainTracer")
    def test_returns_tracer_when_enabled(self, mock_tracer_cls, _mock_enabled):
        """Should return a LangChainTracer instance when tracing is enabled."""
        from yamlgraph.utils.tracing import create_tracer

        tracer = create_tracer()
        assert tracer is mock_tracer_cls.return_value

    @pytest.mark.req("REQ-YG-047")
    @patch("yamlgraph.utils.tracing.is_tracing_enabled", return_value=True)
    @patch("langchain_core.tracers.LangChainTracer")
    def test_passes_project_name(self, mock_tracer_cls, _mock_enabled):
        """Should pass project_name to LangChainTracer."""
        from yamlgraph.utils.tracing import create_tracer

        create_tracer(project_name="my-project")
        mock_tracer_cls.assert_called_once_with(project_name="my-project")

    @pytest.mark.req("REQ-YG-047")
    @patch("yamlgraph.utils.tracing.is_tracing_enabled", return_value=True)
    @patch("langchain_core.tracers.LangChainTracer")
    def test_default_project_name_is_none(self, mock_tracer_cls, _mock_enabled):
        """Should default to project_name=None (LangSmith uses env var)."""
        from yamlgraph.utils.tracing import create_tracer

        create_tracer()
        mock_tracer_cls.assert_called_once_with(project_name=None)


# =============================================================================
# get_trace_url
# =============================================================================


class TestGetTraceUrl:
    """Tests for safe URL retrieval."""

    @pytest.mark.req("REQ-YG-047")
    def test_returns_url_from_tracer(self):
        """Should return the URL from tracer.get_run_url()."""
        from yamlgraph.utils.tracing import get_trace_url

        tracer = MagicMock()
        tracer.get_run_url.return_value = "https://smith.langchain.com/o/xxx/r/yyy"
        assert get_trace_url(tracer) == "https://smith.langchain.com/o/xxx/r/yyy"

    @pytest.mark.req("REQ-YG-047")
    def test_returns_none_when_tracer_is_none(self):
        """Should return None when tracer is None."""
        from yamlgraph.utils.tracing import get_trace_url

        assert get_trace_url(None) is None

    @pytest.mark.req("REQ-YG-047")
    def test_returns_none_on_exception(self):
        """Should return None and not raise when get_run_url fails."""
        from yamlgraph.utils.tracing import get_trace_url

        tracer = MagicMock()
        tracer.get_run_url.side_effect = Exception("Network error")
        assert get_trace_url(tracer) is None

    @pytest.mark.req("REQ-YG-047")
    def test_returns_none_when_no_latest_run(self):
        """Should return None when tracer has no latest_run."""
        from yamlgraph.utils.tracing import get_trace_url

        tracer = MagicMock()
        tracer.latest_run = None
        tracer.get_run_url.side_effect = AttributeError("no run")
        assert get_trace_url(tracer) is None


# =============================================================================
# share_trace
# =============================================================================


class TestShareTrace:
    """Tests for trace sharing."""

    @pytest.mark.req("REQ-YG-047")
    def test_returns_public_url(self):
        """Should call share_run and return the public URL."""
        from yamlgraph.utils.tracing import share_trace

        tracer = MagicMock()
        tracer.latest_run.id = "run-123"
        tracer.client.share_run.return_value = (
            "https://smith.langchain.com/public/xxx/r/run-123"
        )
        url = share_trace(tracer)
        tracer.client.share_run.assert_called_once_with("run-123")
        assert url == "https://smith.langchain.com/public/xxx/r/run-123"

    @pytest.mark.req("REQ-YG-047")
    def test_returns_none_when_tracer_is_none(self):
        """Should return None when tracer is None."""
        from yamlgraph.utils.tracing import share_trace

        assert share_trace(None) is None

    @pytest.mark.req("REQ-YG-047")
    def test_returns_none_on_exception(self):
        """Should return None and not raise when share_run fails."""
        from yamlgraph.utils.tracing import share_trace

        tracer = MagicMock()
        tracer.latest_run.id = "run-123"
        tracer.client.share_run.side_effect = Exception("API error")
        assert share_trace(tracer) is None

    @pytest.mark.req("REQ-YG-047")
    def test_returns_none_when_no_latest_run(self):
        """Should return None when tracer has no latest_run."""
        from yamlgraph.utils.tracing import share_trace

        tracer = MagicMock()
        tracer.latest_run = None
        assert share_trace(tracer) is None


# =============================================================================
# inject_tracer_config
# =============================================================================


class TestInjectTracerConfig:
    """Tests for config dict manipulation."""

    @pytest.mark.req("REQ-YG-047")
    def test_adds_callbacks_to_empty_config(self):
        """Should add callbacks list to empty config."""
        from yamlgraph.utils.tracing import inject_tracer_config

        tracer = MagicMock()
        config = {}
        result = inject_tracer_config(config, tracer)
        assert result["callbacks"] == [tracer]

    @pytest.mark.req("REQ-YG-047")
    def test_preserves_existing_config(self):
        """Should not overwrite existing configurable."""
        from yamlgraph.utils.tracing import inject_tracer_config

        tracer = MagicMock()
        config = {"configurable": {"thread_id": "t1"}}
        result = inject_tracer_config(config, tracer)
        assert result["configurable"]["thread_id"] == "t1"
        assert result["callbacks"] == [tracer]

    @pytest.mark.req("REQ-YG-047")
    def test_returns_unchanged_when_tracer_none(self):
        """Should return config unchanged when tracer is None."""
        from yamlgraph.utils.tracing import inject_tracer_config

        config = {"configurable": {"thread_id": "t1"}}
        result = inject_tracer_config(config, None)
        assert "callbacks" not in result
        assert result["configurable"]["thread_id"] == "t1"

    @pytest.mark.req("REQ-YG-047")
    def test_appends_to_existing_callbacks(self):
        """Should append tracer to existing callbacks list."""
        from yamlgraph.utils.tracing import inject_tracer_config

        tracer = MagicMock()
        existing_cb = MagicMock()
        config = {"callbacks": [existing_cb]}
        result = inject_tracer_config(config, tracer)
        assert result["callbacks"] == [existing_cb, tracer]
