"""Tests for synthesize prompt.

TDD Phase 4: LLM combines discovery findings into analysis.
"""

from pathlib import Path

import pytest
import yaml

PROMPT_PATH = Path(__file__).parents[2] / "prompts" / "impl-agent" / "synthesize.yaml"


class TestSynthesizePromptStructure:
    """Test prompt file structure and content."""

    @pytest.fixture
    def prompt_content(self) -> dict:
        """Load the prompt YAML."""
        assert PROMPT_PATH.exists(), f"Prompt not found: {PROMPT_PATH}"
        with open(PROMPT_PATH) as f:
            return yaml.safe_load(f)

    def test_has_required_sections(self, prompt_content):
        """Should have system, user, and schema sections."""
        assert "system" in prompt_content
        assert "user" in prompt_content
        assert "schema" in prompt_content

    def test_has_metadata(self, prompt_content):
        """Should have metadata with description and model."""
        assert "metadata" in prompt_content
        metadata = prompt_content["metadata"]
        assert "description" in metadata
        assert "model" in metadata or "provider" in metadata

    def test_system_covers_focus_areas(self, prompt_content):
        """System prompt should mention key focus areas."""
        system = prompt_content["system"].lower()
        # Must analyze these aspects
        assert "file" in system or "target" in system
        assert "depend" in system or "caller" in system
        assert "test" in system
        assert "pattern" in system

    def test_user_includes_discovery_findings(self, prompt_content):
        """User template should include discovery_findings variable."""
        user = prompt_content["user"]
        assert "{discovery_findings}" in user or "discovery_findings" in user

    def test_user_includes_story(self, prompt_content):
        """User template should include story context."""
        user = prompt_content["user"]
        assert "{story}" in user or "story" in user


class TestSynthesizeSchema:
    """Test the output schema structure."""

    @pytest.fixture
    def schema(self) -> dict:
        """Load the schema from prompt."""
        with open(PROMPT_PATH) as f:
            content = yaml.safe_load(f)
        return content.get("schema", {})

    def test_schema_has_summary(self, schema):
        """Schema should include summary field."""
        props = schema.get("properties", {})
        assert "summary" in props

    def test_schema_has_target_files(self, schema):
        """Schema should include target_files array."""
        props = schema.get("properties", {})
        assert "target_files" in props
        assert props["target_files"].get("type") == "array"

    def test_schema_has_dependencies(self, schema):
        """Schema should include dependencies."""
        props = schema.get("properties", {})
        assert "dependencies" in props or "callers" in props

    def test_schema_has_test_coverage(self, schema):
        """Schema should include test coverage info."""
        props = schema.get("properties", {})
        assert "test_coverage" in props or "tests" in props

    def test_schema_has_patterns(self, schema):
        """Schema should include patterns to follow."""
        props = schema.get("properties", {})
        assert "patterns_to_follow" in props or "patterns" in props
