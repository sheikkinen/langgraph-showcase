"""Tests for FR-009: JSON Schema Export for IDE Support.

TDD RED phase - these tests will fail until implementation.
"""

import json
from pathlib import Path

import pytest


class TestExportGraphJsonSchema:
    """Tests for export_graph_json_schema function."""

    def test_import_function(self) -> None:
        """Test function can be imported."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        assert callable(export_graph_json_schema)

    def test_returns_valid_json_schema(self) -> None:
        """Test export returns a valid JSON Schema dict."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        schema = export_graph_json_schema()

        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"

    def test_includes_schema_id(self) -> None:
        """Test schema includes $id."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        schema = export_graph_json_schema()

        assert "$id" in schema
        assert "yamlgraph" in schema["$id"]

    def test_includes_title_and_description(self) -> None:
        """Test schema has title and description."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        schema = export_graph_json_schema()

        assert "title" in schema
        assert "description" in schema

    def test_includes_required_properties(self) -> None:
        """Test schema defines required properties."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        schema = export_graph_json_schema()

        assert "properties" in schema
        props = schema["properties"]
        assert "nodes" in props
        assert "edges" in props

    def test_includes_node_types_enum(self) -> None:
        """Test schema includes node type reference."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        schema = export_graph_json_schema()

        # Check schema has NodeConfig definition with type field
        schema_json = json.dumps(schema)
        assert "NodeConfig" in schema_json
        assert '"type"' in schema_json
        # The default value shows llm is a valid type
        assert "llm" in schema_json

    def test_includes_on_error_enum(self) -> None:
        """Test schema includes on_error field."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        schema = export_graph_json_schema()

        schema_json = json.dumps(schema)
        # on_error field exists in schema
        assert "on_error" in schema_json

    def test_includes_field_descriptions(self) -> None:
        """Test schema includes Pydantic Field descriptions."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        schema = export_graph_json_schema()

        # Look for any description in the schema
        schema_json = json.dumps(schema)
        assert "description" in schema_json

    def test_schema_is_serializable(self) -> None:
        """Test schema can be serialized to JSON string."""
        from yamlgraph.models.graph_schema import export_graph_json_schema

        schema = export_graph_json_schema()

        # Should not raise
        json_str = json.dumps(schema, indent=2)
        assert len(json_str) > 100

        # Should be parseable back
        parsed = json.loads(json_str)
        assert parsed == schema


class TestGetSchemaPath:
    """Tests for get_schema_path function."""

    def test_import_function(self) -> None:
        """Test function can be imported from package."""
        from yamlgraph import get_schema_path

        assert callable(get_schema_path)

    def test_returns_path(self) -> None:
        """Test function returns a Path object."""
        from yamlgraph import get_schema_path

        result = get_schema_path()

        assert isinstance(result, Path)

    def test_path_ends_with_json(self) -> None:
        """Test path points to JSON file."""
        from yamlgraph import get_schema_path

        result = get_schema_path()

        assert result.suffix == ".json"

    def test_bundled_schema_exists(self) -> None:
        """Test bundled schema file exists at returned path."""
        from yamlgraph import get_schema_path

        result = get_schema_path()

        assert result.exists(), f"Bundled schema not found at {result}"

    def test_bundled_schema_is_valid_json(self) -> None:
        """Test bundled schema is valid JSON."""
        from yamlgraph import get_schema_path

        schema_path = get_schema_path()
        content = schema_path.read_text()
        schema = json.loads(content)

        assert "$schema" in schema


class TestSchemaCliCommands:
    """Tests for CLI schema commands."""

    def test_schema_export_command_exists(self) -> None:
        """Test schema export CLI command is registered."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        # Parse with schema export - should not error
        args = parser.parse_args(["schema", "export"])
        assert args.schema_command == "export"

    def test_schema_export_with_output_flag(self) -> None:
        """Test schema export accepts --output flag."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["schema", "export", "--output", "schema.json"])
        assert args.output == "schema.json"

    def test_schema_path_command_exists(self) -> None:
        """Test schema path CLI command is registered."""
        from yamlgraph.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["schema", "path"])
        assert args.schema_command == "path"

    def test_cmd_schema_export_function(self) -> None:
        """Test cmd_schema_export handler exists."""
        from yamlgraph.cli.schema_commands import cmd_schema_export

        assert callable(cmd_schema_export)

    def test_cmd_schema_path_function(self) -> None:
        """Test cmd_schema_path handler exists."""
        from yamlgraph.cli.schema_commands import cmd_schema_path

        assert callable(cmd_schema_path)

    def test_cmd_schema_export_outputs_json(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test schema export prints valid JSON to stdout."""
        from argparse import Namespace

        from yamlgraph.cli.schema_commands import cmd_schema_export

        args = Namespace(output=None)
        cmd_schema_export(args)

        captured = capsys.readouterr()
        schema = json.loads(captured.out)
        assert "$schema" in schema

    def test_cmd_schema_export_writes_file(self, tmp_path: Path) -> None:
        """Test schema export writes to file when --output given."""
        from argparse import Namespace

        from yamlgraph.cli.schema_commands import cmd_schema_export

        output_file = tmp_path / "schema.json"
        args = Namespace(output=str(output_file))
        cmd_schema_export(args)

        assert output_file.exists()
        schema = json.loads(output_file.read_text())
        assert "$schema" in schema

    def test_cmd_schema_path_prints_path(self, capsys: pytest.CaptureFixture) -> None:
        """Test schema path prints path to bundled schema."""
        from argparse import Namespace

        from yamlgraph.cli.schema_commands import cmd_schema_path

        args = Namespace()
        cmd_schema_path(args)

        captured = capsys.readouterr()
        path = Path(captured.out.strip())
        assert path.suffix == ".json"

    def test_cmd_schema_dispatch_export(self, capsys: pytest.CaptureFixture) -> None:
        """Test schema dispatch routes to export command."""
        from argparse import Namespace

        from yamlgraph.cli.schema_commands import cmd_schema_dispatch

        args = Namespace(schema_command="export", output=None)
        cmd_schema_dispatch(args)

        captured = capsys.readouterr()
        # Should output valid JSON
        schema = json.loads(captured.out)
        assert "$schema" in schema

    def test_cmd_schema_dispatch_path(self, capsys: pytest.CaptureFixture) -> None:
        """Test schema dispatch routes to path command."""
        from argparse import Namespace

        from yamlgraph.cli.schema_commands import cmd_schema_dispatch

        args = Namespace(schema_command="path")
        cmd_schema_dispatch(args)

        captured = capsys.readouterr()
        path = Path(captured.out.strip())
        assert path.suffix == ".json"

    def test_cmd_schema_dispatch_unknown_command(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test schema dispatch handles unknown command."""
        from argparse import Namespace

        from yamlgraph.cli.schema_commands import cmd_schema_dispatch

        args = Namespace(schema_command="invalid")
        with pytest.raises(SystemExit) as exc_info:
            cmd_schema_dispatch(args)
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Unknown schema command" in captured.out
