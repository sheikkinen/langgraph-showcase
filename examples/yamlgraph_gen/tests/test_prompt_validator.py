"""Tests for prompt_validator module."""

from pathlib import Path

from examples.yamlgraph_gen.tools.prompt_validator import (
    validate_prompt_directory,
    validate_prompt_file,
)


class TestValidatePromptFile:
    """Tests for validate_prompt_file function."""

    def test_valid_prompt(self, tmp_path: Path) -> None:
        """Valid prompt file passes validation."""
        prompt_file = tmp_path / "test.yaml"
        prompt_file.write_text("""
system: |
  You are helpful.

user: |
  Help me with {topic}.
""")

        result = validate_prompt_file(str(prompt_file))

        assert result["valid"] is True
        assert result["errors"] == []

    def test_valid_prompt_with_schema(self, tmp_path: Path) -> None:
        """Prompt with valid schema passes."""
        prompt_file = tmp_path / "test.yaml"
        prompt_file.write_text("""
system: You are helpful.
user: Help with {topic}.
schema:
  name: Result
  fields:
    output:
      type: str
      description: The result
""")

        result = validate_prompt_file(str(prompt_file))

        assert result["valid"] is True

    def test_missing_system_key(self, tmp_path: Path) -> None:
        """Prompt without system key fails."""
        prompt_file = tmp_path / "test.yaml"
        prompt_file.write_text("""
user: Help me.
""")

        result = validate_prompt_file(str(prompt_file))

        assert result["valid"] is False
        assert any("system" in e for e in result["errors"])

    def test_missing_user_key(self, tmp_path: Path) -> None:
        """Prompt without user key fails."""
        prompt_file = tmp_path / "test.yaml"
        prompt_file.write_text("""
system: You are helpful.
""")

        result = validate_prompt_file(str(prompt_file))

        assert result["valid"] is False
        assert any("user" in e for e in result["errors"])

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Invalid YAML fails."""
        prompt_file = tmp_path / "test.yaml"
        prompt_file.write_text("""
system: [unclosed
""")

        result = validate_prompt_file(str(prompt_file))

        assert result["valid"] is False
        assert any("Invalid YAML" in e for e in result["errors"])

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file fails."""
        result = validate_prompt_file(str(tmp_path / "missing.yaml"))

        assert result["valid"] is False
        assert any("not found" in e for e in result["errors"])

    def test_unknown_keys_warning(self, tmp_path: Path) -> None:
        """Unknown keys produce warnings."""
        prompt_file = tmp_path / "test.yaml"
        prompt_file.write_text("""
system: You are helpful.
user: Help me.
custom_key: something
""")

        result = validate_prompt_file(str(prompt_file))

        assert result["valid"] is True  # Still valid
        assert any("custom_key" in w for w in result["warnings"])

    def test_schema_missing_name(self, tmp_path: Path) -> None:
        """Schema without name fails."""
        prompt_file = tmp_path / "test.yaml"
        prompt_file.write_text("""
system: You are helpful.
user: Help me.
schema:
  fields:
    output:
      type: str
""")

        result = validate_prompt_file(str(prompt_file))

        assert result["valid"] is False
        assert any("name" in e for e in result["errors"])


class TestValidatePromptDirectory:
    """Tests for validate_prompt_directory function."""

    def test_all_valid(self, tmp_path: Path) -> None:
        """Directory with all valid prompts passes."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        (prompts_dir / "a.yaml").write_text("system: A\nuser: Do A")
        (prompts_dir / "b.yaml").write_text("system: B\nuser: Do B")

        result = validate_prompt_directory(str(prompts_dir))

        assert result["valid"] is True
        assert result["structure_valid"] is True
        assert len(result["results"]) == 2

    def test_some_invalid(self, tmp_path: Path) -> None:
        """Directory with some invalid prompts fails."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        (prompts_dir / "valid.yaml").write_text("system: A\nuser: Do A")
        (prompts_dir / "invalid.yaml").write_text("user: Missing system")

        result = validate_prompt_directory(str(prompts_dir))

        assert result["valid"] is False
        assert len(result["structure_errors"]) > 0

    def test_missing_directory(self, tmp_path: Path) -> None:
        """Missing directory fails."""
        result = validate_prompt_directory(str(tmp_path / "missing"))

        assert result["valid"] is False
        assert any("not found" in e for e in result["structure_errors"])

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory passes (no files to validate)."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        result = validate_prompt_directory(str(prompts_dir))

        assert result["valid"] is True
        assert result["results"] == {}
