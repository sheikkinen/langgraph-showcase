"""Tests for legacy CLI command deprecation (FR-012-2).

TDD tests for deprecation warnings on legacy commands:
- cmd_list_runs
- cmd_trace
- cmd_export
"""

import warnings
from argparse import Namespace
from unittest.mock import MagicMock, patch


class TestCmdListRunsDeprecation:
    """Tests for cmd_list_runs deprecation warning."""

    def test_cmd_list_runs_emits_deprecation_warning(self) -> None:
        """cmd_list_runs should emit DeprecationWarning."""
        from yamlgraph.cli.commands import cmd_list_runs

        args = Namespace(limit=10)

        with patch("yamlgraph.storage.YamlGraphDB") as mock_db:
            mock_db.return_value.list_runs.return_value = []

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                cmd_list_runs(args)

                # Should have emitted at least one DeprecationWarning
                deprecation_warnings = [
                    x for x in w if issubclass(x.category, DeprecationWarning)
                ]
                assert len(deprecation_warnings) >= 1

    def test_cmd_list_runs_warning_mentions_langsmith(self) -> None:
        """Deprecation warning should mention LangSmith as replacement."""
        from yamlgraph.cli.commands import cmd_list_runs

        args = Namespace(limit=10)

        with patch("yamlgraph.storage.YamlGraphDB") as mock_db:
            mock_db.return_value.list_runs.return_value = []

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                cmd_list_runs(args)

                deprecation_warnings = [
                    x for x in w if issubclass(x.category, DeprecationWarning)
                ]
                assert len(deprecation_warnings) >= 1
                warning_message = str(deprecation_warnings[0].message)
                assert "LangSmith" in warning_message or "langsmith" in warning_message.lower()


class TestCmdTraceDeprecation:
    """Tests for cmd_trace deprecation warning."""

    def test_cmd_trace_emits_deprecation_warning(self) -> None:
        """cmd_trace should emit DeprecationWarning."""
        from yamlgraph.cli.commands import cmd_trace

        args = Namespace(run_id=None, verbose=False)

        with patch("yamlgraph.utils.get_latest_run_id", return_value=None):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                cmd_trace(args)

                deprecation_warnings = [
                    x for x in w if issubclass(x.category, DeprecationWarning)
                ]
                assert len(deprecation_warnings) >= 1

    def test_cmd_trace_warning_mentions_langsmith(self) -> None:
        """Deprecation warning should mention LangSmith as replacement."""
        from yamlgraph.cli.commands import cmd_trace

        args = Namespace(run_id=None, verbose=False)

        with patch("yamlgraph.utils.get_latest_run_id", return_value=None):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                cmd_trace(args)

                deprecation_warnings = [
                    x for x in w if issubclass(x.category, DeprecationWarning)
                ]
                assert len(deprecation_warnings) >= 1
                warning_message = str(deprecation_warnings[0].message)
                assert "LangSmith" in warning_message


class TestCmdExportDeprecation:
    """Tests for cmd_export deprecation warning."""

    def test_cmd_export_emits_deprecation_warning(self) -> None:
        """cmd_export should emit DeprecationWarning."""
        from yamlgraph.cli.commands import cmd_export

        args = Namespace(thread_id="test-123")

        with patch("yamlgraph.storage.YamlGraphDB") as mock_db:
            mock_db.return_value.load_state.return_value = None

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                cmd_export(args)

                deprecation_warnings = [
                    x for x in w if issubclass(x.category, DeprecationWarning)
                ]
                assert len(deprecation_warnings) >= 1

    def test_cmd_export_warning_mentions_graph_run(self) -> None:
        """Deprecation warning should mention 'graph run --export' as replacement."""
        from yamlgraph.cli.commands import cmd_export

        args = Namespace(thread_id="test-123")

        with patch("yamlgraph.storage.YamlGraphDB") as mock_db:
            mock_db.return_value.load_state.return_value = None

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                cmd_export(args)

                deprecation_warnings = [
                    x for x in w if issubclass(x.category, DeprecationWarning)
                ]
                assert len(deprecation_warnings) >= 1
                warning_message = str(deprecation_warnings[0].message)
                assert "graph run" in warning_message and "--export" in warning_message


class TestCmdRunDeadCode:
    """Tests to verify cmd_run is dead code and has been removed."""

    def test_cmd_run_not_in_cli_init(self) -> None:
        """cmd_run should NOT be wired up in CLI __init__.py."""
        from yamlgraph import cli

        # Check that cmd_run is NOT exposed in CLI's public interface
        assert not hasattr(cli, "cmd_run")

    def test_cmd_run_removed_from_commands(self) -> None:
        """cmd_run should be removed from commands.py (dead code cleanup)."""
        # The old 'yamlgraph run' command was dead code - never wired to CLI
        # It has been removed as part of FR-012-2
        from yamlgraph.cli import commands

        assert not hasattr(commands, "cmd_run")
