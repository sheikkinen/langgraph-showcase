"""Tests for CLI package structure (Phase 7.1).

TDD tests for splitting cli.py into a cli/ package.
"""

import argparse

# =============================================================================
# Package Structure Tests
# =============================================================================


class TestCLIPackageStructure:
    """Tests for CLI package imports."""

    def test_cli_package_importable(self):
        """yamlgraph.cli should be importable as package."""
        import yamlgraph.cli

        assert yamlgraph.cli is not None

    def test_main_function_available(self):
        """main() should be available from package."""
        from yamlgraph.cli import main

        assert callable(main)

    def test_validators_submodule_exists(self):
        """validators submodule should exist."""
        from yamlgraph.cli import validators

        assert validators is not None

    def test_validate_run_args_in_validators(self):
        """validate_run_args should be in validators module."""
        from yamlgraph.cli.validators import validate_run_args

        assert callable(validate_run_args)

    def test_commands_submodule_exists(self):
        """commands submodule should exist."""
        from yamlgraph.cli import commands

        assert commands is not None

    def test_cmd_list_runs_in_commands(self):
        """cmd_list_runs should be in commands module."""
        from yamlgraph.cli.commands import cmd_list_runs

        assert callable(cmd_list_runs)


# =============================================================================
# Validator Tests (moved from cli module)
# =============================================================================


class TestValidatorsModule:
    """Tests for validators module functionality."""

    def _create_run_args(self, topic="test topic", word_count=300, style="informative"):
        """Helper to create run args namespace."""
        return argparse.Namespace(
            topic=topic,
            word_count=word_count,
            style=style,
        )

    def test_validate_run_args_valid(self):
        """Valid run args pass validation."""
        from yamlgraph.cli.validators import validate_run_args

        args = self._create_run_args()
        assert validate_run_args(args) is True

    def test_validate_run_args_empty_topic(self):
        """Empty topic fails validation."""
        from yamlgraph.cli.validators import validate_run_args

        args = self._create_run_args(topic="")
        assert validate_run_args(args) is False
