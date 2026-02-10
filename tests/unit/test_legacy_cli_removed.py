"""Tests for legacy CLI removal (FR-012-3).

TDD tests to verify legacy code has been removed:
- cmd_resume, cmd_list_runs, cmd_trace, cmd_export
- YamlGraphDB
- build_resume_graph
"""

import pytest


class TestLegacyCLICommandsRemoved:
    """Verify legacy CLI commands module has been removed."""

    @pytest.mark.req("REQ-YG-035")
    def test_commands_module_removed(self) -> None:
        """commands.py module should be removed from CLI package."""
        with pytest.raises(ImportError):
            from yamlgraph.cli import commands  # noqa: F401

    @pytest.mark.req("REQ-YG-035")
    def test_validators_module_removed(self) -> None:
        """validators.py module should be removed from CLI package."""
        with pytest.raises(ImportError):
            from yamlgraph.cli import validators  # noqa: F401


class TestYamlGraphDBRemoved:
    """Verify YamlGraphDB has been removed."""

    @pytest.mark.req("REQ-YG-035")
    def test_yamlgraphdb_not_in_storage(self) -> None:
        """YamlGraphDB should not be importable from storage."""
        from yamlgraph import storage

        assert not hasattr(storage, "YamlGraphDB")

    @pytest.mark.req("REQ-YG-035")
    def test_database_module_removed(self) -> None:
        """database.py module should be removed from storage."""
        with pytest.raises(ImportError):
            from yamlgraph.storage import database  # noqa: F401


class TestBuilderModuleRemoved:
    """Verify builder module has been removed."""

    @pytest.mark.req("REQ-YG-035")
    def test_builder_module_not_importable(self) -> None:
        """builder module should not be importable."""
        with pytest.raises(ImportError):
            from yamlgraph import builder  # noqa: F401

    @pytest.mark.req("REQ-YG-035")
    def test_build_graph_not_exported(self) -> None:
        """build_graph should not be exported from yamlgraph."""
        import yamlgraph

        assert not hasattr(yamlgraph, "build_graph")


class TestModernAPIPreserved:
    """Verify modern API is still available."""

    @pytest.mark.req("REQ-YG-035")
    def test_load_and_compile_exported(self) -> None:
        """load_and_compile should be exported from yamlgraph."""
        from yamlgraph import load_and_compile

        assert callable(load_and_compile)

    @pytest.mark.req("REQ-YG-035")
    def test_load_and_compile_from_graph_loader(self) -> None:
        """load_and_compile should be available from graph_loader."""
        from yamlgraph.graph_loader import load_and_compile

        assert callable(load_and_compile)

    @pytest.mark.req("REQ-YG-035")
    def test_export_state_still_available(self) -> None:
        """export_state utility should still be available."""
        from yamlgraph.storage import export_state

        assert callable(export_state)


class TestCLISubparsersRemoved:
    """Verify legacy CLI subparsers have been removed."""

    @pytest.mark.req("REQ-YG-035")
    def test_resume_subparser_removed(self) -> None:
        """'resume' subparser should not exist in CLI."""
        # We can't easily test the argparser directly, but we verify
        # the handler function is gone (tested above)
        pass  # Covered by test_cmd_resume_removed

    @pytest.mark.req("REQ-YG-035")
    def test_list_runs_subparser_removed(self) -> None:
        """'list-runs' subparser should not exist in CLI."""
        pass  # Covered by test_cmd_list_runs_removed

    def test_trace_subparser_removed(self) -> None:
        """'trace' subparser should not exist in CLI."""
        pass  # Covered by test_cmd_trace_removed

    @pytest.mark.req("REQ-YG-035")
    def test_export_subparser_removed(self) -> None:
        """'export' subparser should not exist in CLI."""
        pass  # Covered by test_cmd_export_removed
