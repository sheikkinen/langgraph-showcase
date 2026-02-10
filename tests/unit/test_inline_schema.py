"""Tests for YAML inline schema integration with node factory.

TDD: RED phase - tests for loading output_model from prompt YAML schema block.
"""

import pytest


class TestInlineSchemaIntegration:
    """Test node factory uses inline schema from prompt YAML."""

    @pytest.mark.req("REQ-YG-044")
    def test_node_uses_inline_schema_from_prompt(self, tmp_path, monkeypatch):
        """Node uses schema defined in prompt YAML instead of output_model."""
        # Create a prompt file with inline schema
        prompt_dir = tmp_path / "prompts" / "test"
        prompt_dir.mkdir(parents=True)

        prompt_file = prompt_dir / "classify.yaml"
        prompt_file.write_text("""
name: classify_tone
version: "1.0"

schema:
  name: InlineClassification
  fields:
    result:
      type: str
      description: "Classification result"
    score:
      type: float
      description: "Confidence score"
      constraints:
        ge: 0.0
        le: 1.0

system: You are a classifier.
user: "Classify: {message}"
""")

        # Patch prompts directory
        monkeypatch.setenv("PROMPTS_DIR", str(tmp_path / "prompts"))

        # Create node without explicit output_model - should use inline schema
        node_config = {
            "type": "llm",
            "prompt": "test/classify",
            # No output_model specified - should load from YAML
        }

        # This should work and detect inline schema
        from yamlgraph.node_factory import get_output_model_for_node

        model = get_output_model_for_node(node_config, str(tmp_path / "prompts"))

        assert model is not None
        assert model.__name__ == "InlineClassification"

        # Verify model works
        instance = model(result="positive", score=0.95)
        assert instance.result == "positive"
        assert instance.score == 0.95

    @pytest.mark.req("REQ-YG-044")
    def test_explicit_output_model_overrides_inline_schema(self, tmp_path, monkeypatch):
        """Explicit output_model in node config takes precedence."""
        prompt_dir = tmp_path / "prompts" / "test"
        prompt_dir.mkdir(parents=True)

        prompt_file = prompt_dir / "with_schema.yaml"
        prompt_file.write_text("""
name: test_prompt
schema:
  name: InlineModel
  fields:
    value: {type: str}
system: Test
user: "{input}"
""")

        monkeypatch.setenv("PROMPTS_DIR", str(tmp_path / "prompts"))

        # Node config has explicit output_model
        node_config = {
            "type": "llm",
            "prompt": "test/with_schema",
            "output_model": "yamlgraph.models.GenericReport",  # Explicit - takes precedence
        }

        from yamlgraph.node_factory import get_output_model_for_node

        model = get_output_model_for_node(node_config, str(tmp_path / "prompts"))

        # Should use explicit model, not inline
        assert model.__name__ == "GenericReport"

    @pytest.mark.req("REQ-YG-044")
    def test_no_schema_returns_none(self, tmp_path, monkeypatch):
        """Prompt without schema returns None for output_model."""
        prompt_dir = tmp_path / "prompts" / "test"
        prompt_dir.mkdir(parents=True)

        prompt_file = prompt_dir / "plain.yaml"
        prompt_file.write_text("""
name: plain_prompt
system: Test
user: "{input}"
""")

        monkeypatch.setenv("PROMPTS_DIR", str(tmp_path / "prompts"))

        node_config = {
            "type": "llm",
            "prompt": "test/plain",
        }

        from yamlgraph.node_factory import get_output_model_for_node

        model = get_output_model_for_node(node_config, str(tmp_path / "prompts"))

        assert model is None


class TestResolvePromptPath:
    """Test resolving prompt name to full file path."""

    @pytest.mark.req("REQ-YG-044")
    def test_resolve_prompt_path(self, tmp_path):
        """Resolve prompt name to full YAML path."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()

        (prompt_dir / "simple.yaml").write_text("name: simple")
        (prompt_dir / "nested").mkdir()
        (prompt_dir / "nested" / "deep.yaml").write_text("name: deep")

        from yamlgraph.utils.prompts import resolve_prompt_path

        # Simple prompt - now returns Path object
        path = resolve_prompt_path("simple", prompt_dir)
        assert path.name == "simple.yaml"

        # Nested prompt
        path = resolve_prompt_path("nested/deep", prompt_dir)
        assert path.name == "deep.yaml"

    @pytest.mark.req("REQ-YG-044")
    def test_resolve_missing_prompt_raises(self, tmp_path):
        """Missing prompt file raises FileNotFoundError."""
        prompt_dir = tmp_path / "prompts"
        prompt_dir.mkdir()

        from yamlgraph.utils.prompts import resolve_prompt_path

        with pytest.raises(FileNotFoundError):
            resolve_prompt_path("nonexistent", prompt_dir)
