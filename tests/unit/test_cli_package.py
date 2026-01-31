"""Tests for CLI package structure (Phase 7.1).

TDD tests for splitting cli.py into a cli/ package.
"""

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

    def test_graph_commands_submodule_exists(self):
        """graph_commands submodule should exist."""
        from yamlgraph.cli import graph_commands

        assert graph_commands is not None

    def test_cmd_graph_dispatch_in_graph_commands(self):
        """cmd_graph_dispatch should be in graph_commands module."""
        from yamlgraph.cli.graph_commands import cmd_graph_dispatch

        assert callable(cmd_graph_dispatch)

    def test_async_flag_in_graph_run_parser(self):
        """--async flag should be available in graph run parser."""

        from yamlgraph.cli import create_parser

        parser = create_parser()
        # Parse valid command with --async flag
        args = parser.parse_args(["graph", "run", "test.yaml", "--async"])
        assert args.use_async is True

    def test_async_flag_default_is_false(self):
        """--async flag should default to False."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "test.yaml"])
        assert args.use_async is False

    def test_async_short_flag(self):
        """-a short flag should work for async."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["graph", "run", "test.yaml", "-a"])
        assert args.use_async is True
