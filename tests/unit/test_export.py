"""Tests for showcase.storage.export module."""

import json


from showcase.storage.export import export_state, _serialize_state
from showcase.models import GeneratedContent


class TestExportState:
    """Tests for export_state function."""

    def test_export_creates_file(self, temp_output_dir, sample_state):
        """Export should create a JSON file."""
        filepath = export_state(sample_state, output_dir=temp_output_dir)
        assert filepath.exists()
        assert filepath.suffix == ".json"

    def test_export_file_contains_valid_json(self, temp_output_dir, sample_state):
        """Exported file should contain valid JSON."""
        filepath = export_state(sample_state, output_dir=temp_output_dir)
        with open(filepath) as f:
            data = json.load(f)
        assert "topic" in data
        assert "thread_id" in data

    def test_export_filename_format(self, temp_output_dir, sample_state):
        """Filename should include prefix and thread_id."""
        filepath = export_state(
            sample_state,
            output_dir=temp_output_dir,
            prefix="test_export",
        )
        assert "test_export" in filepath.name
        assert sample_state["thread_id"] in filepath.name

    def test_export_creates_output_dir(self, tmp_path, sample_state):
        """Export should create output directory if it doesn't exist."""
        new_dir = tmp_path / "new_outputs"
        filepath = export_state(sample_state, output_dir=new_dir)
        assert new_dir.exists()
        assert filepath.exists()


class TestSerializeState:
    """Tests for _serialize_state function."""

    def test_serialize_simple_state(self, empty_state):
        """Simple state should serialize unchanged."""
        result = _serialize_state(empty_state)
        assert result["topic"] == empty_state["topic"]
        assert result["style"] == empty_state["style"]

    def test_serialize_pydantic_models(self):
        """Pydantic models should be converted to dicts."""
        content = GeneratedContent(
            title="Test",
            content="Content",
            word_count=1,
            tags=["tag"],
        )
        state = {"generated": content}
        result = _serialize_state(state)
        assert isinstance(result["generated"], dict)
        assert result["generated"]["title"] == "Test"

    def test_serialize_preserves_none(self, empty_state):
        """None values should be preserved."""
        result = _serialize_state(empty_state)
        assert result["generated"] is None
        assert result["error"] is None
