"""Tests for Phase 6.4: Result Export.

Tests field-based result export with multiple formats.
"""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class SampleModel(BaseModel):
    """Sample model for testing."""

    title: str
    content: str
    tags: list[str] = Field(default_factory=list)


class TestExportResult:
    """Tests for export_result function."""

    def test_export_json_field(self, tmp_path: Path):
        """Export field as JSON file."""
        from yamlgraph.storage.export import export_result

        state = {
            "thread_id": "test-123",
            "generated": SampleModel(title="Test", content="Body", tags=["a", "b"]),
        }
        config = {
            "generated": {"format": "json", "filename": "content.json"},
        }

        paths = export_result(state, config, base_path=tmp_path)

        assert len(paths) == 1
        assert paths[0].name == "content.json"
        assert paths[0].exists()

        data = json.loads(paths[0].read_text())
        assert data["title"] == "Test"
        assert data["content"] == "Body"
        assert data["tags"] == ["a", "b"]

    def test_export_markdown_field(self, tmp_path: Path):
        """Export field as Markdown file."""
        from yamlgraph.storage.export import export_result

        state = {
            "thread_id": "test-456",
            "summary": "This is the summary content.",
        }
        config = {
            "summary": {"format": "markdown", "filename": "summary.md"},
        }

        paths = export_result(state, config, base_path=tmp_path)

        assert len(paths) == 1
        assert paths[0].name == "summary.md"
        content = paths[0].read_text()
        assert "This is the summary content." in content

    def test_export_text_field(self, tmp_path: Path):
        """Export field as plain text."""
        from yamlgraph.storage.export import export_result

        state = {
            "thread_id": "test-789",
            "output": "Plain text output",
        }
        config = {
            "output": {"format": "text", "filename": "output.txt"},
        }

        paths = export_result(state, config, base_path=tmp_path)

        assert len(paths) == 1
        content = paths[0].read_text()
        assert content == "Plain text output"

    def test_export_creates_thread_directory(self, tmp_path: Path):
        """Files are created in thread-specific subdirectory."""
        from yamlgraph.storage.export import export_result

        state = {
            "thread_id": "my-thread-id",
            "result": "data",
        }
        config = {"result": {"format": "text", "filename": "result.txt"}}

        paths = export_result(state, config, base_path=tmp_path)

        # Check directory structure
        assert paths[0].parent.name == "my-thread-id"
        assert paths[0].parent.parent == tmp_path

    def test_export_skips_none_fields(self, tmp_path: Path):
        """Fields with None value are skipped."""
        from yamlgraph.storage.export import export_result

        state = {
            "thread_id": "test",
            "present": "value",
            "missing": None,
        }
        config = {
            "present": {"format": "text", "filename": "present.txt"},
            "missing": {"format": "text", "filename": "missing.txt"},
        }

        paths = export_result(state, config, base_path=tmp_path)

        # Only one file created
        assert len(paths) == 1
        assert paths[0].name == "present.txt"

    def test_export_skips_missing_fields(self, tmp_path: Path):
        """Fields not in state are skipped."""
        from yamlgraph.storage.export import export_result

        state = {"thread_id": "test"}  # No 'data' field
        config = {"data": {"format": "text", "filename": "data.txt"}}

        paths = export_result(state, config, base_path=tmp_path)

        assert len(paths) == 0

    def test_export_multiple_fields(self, tmp_path: Path):
        """Export multiple fields in one call."""
        from yamlgraph.storage.export import export_result

        state = {
            "thread_id": "multi",
            "summary": "Summary text",
            "data": {"key": "value"},
        }
        config = {
            "summary": {"format": "markdown", "filename": "summary.md"},
            "data": {"format": "json", "filename": "data.json"},
        }

        paths = export_result(state, config, base_path=tmp_path)

        assert len(paths) == 2
        names = {p.name for p in paths}
        assert "summary.md" in names
        assert "data.json" in names


class TestSerializeToJson:
    """Tests for JSON serialization helper."""

    def test_serializes_pydantic_model(self):
        """Pydantic models serialize properly."""
        from yamlgraph.storage.export import _serialize_to_json

        model = SampleModel(title="Test", content="Body")
        result = _serialize_to_json(model)
        data = json.loads(result)

        assert data["title"] == "Test"
        assert data["content"] == "Body"

    def test_serializes_dict(self):
        """Regular dicts serialize properly."""
        from yamlgraph.storage.export import _serialize_to_json

        result = _serialize_to_json({"a": 1, "b": [1, 2, 3]})
        data = json.loads(result)

        assert data["a"] == 1
        assert data["b"] == [1, 2, 3]

    def test_serializes_with_indent(self):
        """JSON output is indented."""
        from yamlgraph.storage.export import _serialize_to_json

        result = _serialize_to_json({"key": "value"})
        # Indented JSON has newlines
        assert "\n" in result


class TestPydanticToMarkdown:
    """Tests for Pydantic to Markdown conversion."""

    def test_includes_model_name_as_title(self):
        """Model name becomes the markdown title."""
        from yamlgraph.storage.export import _pydantic_to_markdown

        model = SampleModel(title="Test", content="Body")
        result = _pydantic_to_markdown(model)

        assert result.startswith("# SampleModel")

    def test_formats_list_fields_as_bullets(self):
        """List fields become bullet points."""
        from yamlgraph.storage.export import _pydantic_to_markdown

        model = SampleModel(title="Test", content="Body", tags=["one", "two"])
        result = _pydantic_to_markdown(model)

        assert "- one" in result
        assert "- two" in result

    def test_formats_scalar_fields_bold(self):
        """Scalar fields use bold labels."""
        from yamlgraph.storage.export import _pydantic_to_markdown

        model = SampleModel(title="Test", content="Body")
        result = _pydantic_to_markdown(model)

        assert "**Title**: Test" in result


class TestSerializeToMarkdown:
    """Tests for markdown serialization."""

    def test_pydantic_model_uses_pydantic_to_markdown(self):
        """Pydantic models use _pydantic_to_markdown."""
        from yamlgraph.storage.export import _serialize_to_markdown

        model = SampleModel(title="Test", content="Body")
        result = _serialize_to_markdown(model)

        assert "# SampleModel" in result

    def test_string_value_returns_as_is(self):
        """String values return as-is."""
        from yamlgraph.storage.export import _serialize_to_markdown

        result = _serialize_to_markdown("Just a string")
        assert result == "Just a string"
