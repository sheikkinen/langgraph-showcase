"""Tests for yamlgraph.storage.export module."""

import json
from datetime import datetime

import pytest
from pydantic import BaseModel

from tests.conftest import FixtureGeneratedContent
from yamlgraph.storage.export import (
    _extract_scalar_summary,
    _pydantic_to_markdown,
    _serialize_object,
    _serialize_state,
    _serialize_to_json,
    _serialize_to_markdown,
    export_result,
    export_state,
    list_exports,
    load_export,
)


class TestExportState:
    """Tests for export_state function."""

    @pytest.mark.req("REQ-YG-038")
    def test_export_creates_file(self, temp_output_dir, sample_state):
        """Export should create a JSON file."""
        filepath = export_state(sample_state, output_dir=temp_output_dir)
        assert filepath.exists()
        assert filepath.suffix == ".json"

    @pytest.mark.req("REQ-YG-038")
    def test_export_file_contains_valid_json(self, temp_output_dir, sample_state):
        """Exported file should contain valid JSON."""
        filepath = export_state(sample_state, output_dir=temp_output_dir)
        with open(filepath) as f:
            data = json.load(f)
        assert "topic" in data
        assert "thread_id" in data

    @pytest.mark.req("REQ-YG-038")
    def test_export_filename_format(self, temp_output_dir, sample_state):
        """Filename should include prefix and thread_id."""
        filepath = export_state(
            sample_state,
            output_dir=temp_output_dir,
            prefix="test_export",
        )
        assert "test_export" in filepath.name
        assert sample_state["thread_id"] in filepath.name

    @pytest.mark.req("REQ-YG-038")
    def test_export_creates_output_dir(self, tmp_path, sample_state):
        """Export should create output directory if it doesn't exist."""
        new_dir = tmp_path / "new_outputs"
        filepath = export_state(sample_state, output_dir=new_dir)
        assert new_dir.exists()
        assert filepath.exists()


class TestSerializeState:
    """Tests for _serialize_state function."""

    @pytest.mark.req("REQ-YG-038")
    def test_serialize_simple_state(self, empty_state):
        """Simple state should serialize unchanged."""
        result = _serialize_state(empty_state)
        assert result["topic"] == empty_state["topic"]
        assert result["style"] == empty_state["style"]

    @pytest.mark.req("REQ-YG-038")
    def test_serialize_pydantic_models(self):
        """Pydantic models should be converted to dicts."""
        content = FixtureGeneratedContent(
            title="Test",
            content="Content",
            word_count=1,
            tags=["tag"],
        )
        state = {"generated": content}
        result = _serialize_state(state)
        assert isinstance(result["generated"], dict)
        assert result["generated"]["title"] == "Test"

    @pytest.mark.req("REQ-YG-038")
    def test_serialize_preserves_none(self, empty_state):
        """None values should be preserved."""
        # Add a None field to test serialization
        empty_state["generated"] = None
        result = _serialize_state(empty_state)
        assert result["generated"] is None
        assert result["error"] is None


class TestExportSummaryGeneric:
    """Tests for generic export_summary behavior."""

    @pytest.mark.req("REQ-YG-038")
    def test_export_summary_with_any_pydantic_model(self):
        """export_summary should work with any Pydantic model, not just demo-specific ones."""
        from pydantic import BaseModel

        from yamlgraph.storage.export import export_summary

        class CustomModel(BaseModel):
            name: str
            value: int

        state = {
            "thread_id": "test-123",
            "topic": "custom topic",
            "custom_field": CustomModel(name="test", value=42),
        }

        summary = export_summary(state)

        # Should include core fields
        assert summary["thread_id"] == "test-123"
        assert summary["topic"] == "custom topic"

    @pytest.mark.req("REQ-YG-038")
    def test_export_summary_extracts_scalar_fields(self):
        """export_summary should extract key scalar fields from any model."""
        from pydantic import BaseModel

        from yamlgraph.storage.export import export_summary

        class ReportContent(BaseModel):
            headline: str
            body: str
            author: str

        state = {
            "thread_id": "report-1",
            "topic": "report topic",
            "report": ReportContent(
                headline="Breaking News",
                body="Content here...",
                author="Alice",
            ),
        }

        summary = export_summary(state)
        # Should extract and include scalar fields
        assert "report" in summary or any(k.startswith("report") for k in summary)

    @pytest.mark.req("REQ-YG-038")
    def test_export_summary_no_demo_model_dependencies(self):
        """export_summary should not import demo-specific model types."""
        import ast
        import inspect

        from yamlgraph.storage import export

        source = inspect.getsource(export)
        tree = ast.parse(source)

        demo_models = {
            "GeneratedContent",
            "Analysis",
            "ToneClassification",
            "DraftContent",
            "Critique",
            "SearchResults",
            "FinalReport",
        }

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "schemas" in node.module
            ):
                imported_names = {alias.name for alias in node.names}
                overlap = imported_names & demo_models
                assert not overlap, f"export.py imports demo models: {overlap}"


class TestSerializeObject:
    """Tests for _serialize_object helper."""

    @pytest.mark.req("REQ-YG-038")
    def test_serialize_pydantic_model(self):
        """Should convert Pydantic model to dict."""

        class Item(BaseModel):
            name: str
            value: int

        result = _serialize_object(Item(name="test", value=42))
        assert result == {"name": "test", "value": 42}

    @pytest.mark.req("REQ-YG-038")
    def test_serialize_nested_dict(self):
        """Should recursively serialize dicts."""

        class Inner(BaseModel):
            x: int

        data = {"outer": {"inner": Inner(x=5)}}
        result = _serialize_object(data)
        assert result == {"outer": {"inner": {"x": 5}}}

    @pytest.mark.req("REQ-YG-038")
    def test_serialize_list_with_models(self):
        """Should serialize lists containing models."""

        class Item(BaseModel):
            id: int

        data = [Item(id=1), Item(id=2)]
        result = _serialize_object(data)
        assert result == [{"id": 1}, {"id": 2}]

    @pytest.mark.req("REQ-YG-038")
    def test_serialize_datetime(self):
        """Should convert datetime to ISO format."""
        dt = datetime(2026, 1, 21, 12, 30, 0)
        result = _serialize_object(dt)
        assert result == "2026-01-21T12:30:00"

    @pytest.mark.req("REQ-YG-038")
    def test_serialize_primitive(self):
        """Primitives should pass through unchanged."""
        assert _serialize_object("hello") == "hello"
        assert _serialize_object(42) == 42
        assert _serialize_object(None) is None


class TestListExports:
    """Tests for list_exports function."""

    @pytest.mark.req("REQ-YG-038")
    def test_list_exports_empty_dir(self, tmp_path):
        """Should return empty list for empty directory."""
        result = list_exports(tmp_path)
        assert result == []

    @pytest.mark.req("REQ-YG-038")
    def test_list_exports_nonexistent_dir(self, tmp_path):
        """Should return empty list for nonexistent directory."""
        result = list_exports(tmp_path / "nonexistent")
        assert result == []

    @pytest.mark.req("REQ-YG-038")
    def test_list_exports_finds_files(self, tmp_path):
        """Should find export files matching prefix."""
        (tmp_path / "export_abc_123.json").write_text("{}")
        (tmp_path / "export_def_456.json").write_text("{}")
        (tmp_path / "other_file.json").write_text("{}")

        result = list_exports(tmp_path, prefix="export")
        assert len(result) == 2
        assert all("export" in p.name for p in result)


class TestLoadExport:
    """Tests for load_export function."""

    @pytest.mark.req("REQ-YG-038")
    def test_load_export_reads_json(self, tmp_path):
        """Should load JSON from file."""
        file_path = tmp_path / "test.json"
        file_path.write_text('{"key": "value"}')

        result = load_export(file_path)
        assert result == {"key": "value"}


class TestExportResult:
    """Tests for export_result function."""

    @pytest.mark.req("REQ-YG-038")
    def test_export_result_json_format(self, tmp_path):
        """Should export field as JSON."""

        class Data(BaseModel):
            items: list[str]

        state = {
            "thread_id": "test-123",
            "data": Data(items=["a", "b"]),
        }
        config = {"data": {"format": "json", "filename": "data.json"}}

        paths = export_result(state, config, base_path=tmp_path)

        assert len(paths) == 1
        assert paths[0].name == "data.json"
        content = json.loads(paths[0].read_text())
        assert content["items"] == ["a", "b"]

    @pytest.mark.req("REQ-YG-038")
    def test_export_result_markdown_format(self, tmp_path):
        """Should export field as Markdown."""

        class Report(BaseModel):
            title: str
            items: list[str]

        state = {
            "thread_id": "test-456",
            "report": Report(title="Test", items=["one", "two"]),
        }
        config = {"report": {"format": "markdown", "filename": "report.md"}}

        paths = export_result(state, config, base_path=tmp_path)

        assert len(paths) == 1
        content = paths[0].read_text()
        assert "# Report" in content
        assert "- one" in content

    @pytest.mark.req("REQ-YG-038")
    def test_export_result_skips_none_fields(self, tmp_path):
        """Should skip fields that are None."""
        state = {"thread_id": "test", "missing": None}
        config = {"missing": {"format": "json", "filename": "missing.json"}}

        paths = export_result(state, config, base_path=tmp_path)
        assert paths == []


class TestPydanticToMarkdown:
    """Tests for _pydantic_to_markdown helper."""

    @pytest.mark.req("REQ-YG-038")
    def test_converts_model_to_markdown(self):
        """Should convert Pydantic model to Markdown."""

        class Summary(BaseModel):
            headline: str
            count: int
            tags: list[str]

        model = Summary(headline="Breaking News", count=5, tags=["news", "urgent"])
        result = _pydantic_to_markdown(model)

        assert "# Summary" in result
        assert "**Headline**: Breaking News" in result
        assert "**Count**: 5" in result
        assert "## Tags" in result
        assert "- news" in result
        assert "- urgent" in result


class TestExtractScalarSummary:
    """Tests for _extract_scalar_summary helper."""

    @pytest.mark.req("REQ-YG-038")
    def test_extracts_scalar_fields(self):
        """Should extract int, float, bool fields."""

        class Stats(BaseModel):
            count: int
            score: float
            active: bool

        result = _extract_scalar_summary(Stats(count=10, score=0.95, active=True))
        assert result["count"] == 10
        assert result["score"] == 0.95
        assert result["active"] is True

    @pytest.mark.req("REQ-YG-038")
    def test_truncates_long_strings(self):
        """Should truncate strings longer than 100 chars."""

        class Content(BaseModel):
            text: str

        long_text = "x" * 150
        result = _extract_scalar_summary(Content(text=long_text))
        assert len(result["text"]) == 103  # 100 + "..."
        assert result["text"].endswith("...")

    @pytest.mark.req("REQ-YG-038")
    def test_counts_list_items(self):
        """Should count list items instead of including full list."""

        class Data(BaseModel):
            items: list[str]

        result = _extract_scalar_summary(Data(items=["a", "b", "c", "d"]))
        assert result["items_count"] == 4


class TestSerializeToJson:
    """Tests for _serialize_to_json helper."""

    @pytest.mark.req("REQ-YG-038")
    def test_serializes_pydantic_model(self):
        """Should use model_dump_json for Pydantic models."""

        class Item(BaseModel):
            name: str

        result = _serialize_to_json(Item(name="test"))
        assert '"name": "test"' in result

    @pytest.mark.req("REQ-YG-038")
    def test_serializes_dict(self):
        """Should serialize dicts with json.dumps."""
        result = _serialize_to_json({"key": "value"})
        parsed = json.loads(result)
        assert parsed == {"key": "value"}


class TestSerializeToMarkdown:
    """Tests for _serialize_to_markdown helper."""

    @pytest.mark.req("REQ-YG-038")
    def test_converts_pydantic_to_markdown(self):
        """Should convert Pydantic model to Markdown."""

        class Doc(BaseModel):
            title: str

        result = _serialize_to_markdown(Doc(title="Test"))
        assert "# Doc" in result

    @pytest.mark.req("REQ-YG-038")
    def test_converts_string_unchanged(self):
        """Should return strings as-is."""
        result = _serialize_to_markdown("plain text")
        assert result == "plain text"
