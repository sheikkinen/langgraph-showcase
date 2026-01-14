"""Tests for showcase.config module."""

from showcase.config import (
    DATABASE_PATH,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    MAX_TOPIC_LENGTH,
    MAX_WORD_COUNT,
    MIN_WORD_COUNT,
    OUTPUTS_DIR,
    PACKAGE_ROOT,
    PROJECT_ROOT,
    PROMPTS_DIR,
    VALID_STYLES,
)


class TestPaths:
    """Tests for path configuration."""

    def test_package_root_exists(self):
        """Package root directory should exist."""
        assert PACKAGE_ROOT.exists()
        assert PACKAGE_ROOT.is_dir()

    def test_project_root_exists(self):
        """Project root directory should exist."""
        assert PROJECT_ROOT.exists()
        assert PROJECT_ROOT.is_dir()

    def test_prompts_dir_exists(self):
        """Prompts directory should exist."""
        assert PROMPTS_DIR.exists()
        assert PROMPTS_DIR.is_dir()

    def test_prompts_dir_has_yaml_files(self):
        """Prompts directory should contain YAML files."""
        yaml_files = list(PROMPTS_DIR.glob("*.yaml"))
        assert len(yaml_files) > 0

    def test_outputs_dir_path(self):
        """Outputs directory path should be under project root."""
        assert OUTPUTS_DIR.parent == PROJECT_ROOT

    def test_database_path(self):
        """Database path should be in outputs directory."""
        assert DATABASE_PATH.parent == OUTPUTS_DIR
        assert DATABASE_PATH.suffix == ".db"


class TestLLMConfig:
    """Tests for LLM configuration."""

    def test_default_model_is_string(self):
        """Default model should be a non-empty string."""
        assert isinstance(DEFAULT_MODEL, str)
        assert len(DEFAULT_MODEL) > 0

    def test_default_temperature_range(self):
        """Default temperature should be in valid range."""
        assert 0.0 <= DEFAULT_TEMPERATURE <= 1.0

    def test_default_max_tokens_positive(self):
        """Max tokens should be positive."""
        assert DEFAULT_MAX_TOKENS > 0


class TestCLIConstraints:
    """Tests for CLI validation constraints."""

    def test_topic_length_constraint(self):
        """Max topic length should be reasonable."""
        assert MAX_TOPIC_LENGTH > 0
        assert MAX_TOPIC_LENGTH <= 10000

    def test_word_count_constraints(self):
        """Word count constraints should be valid."""
        assert MIN_WORD_COUNT > 0
        assert MAX_WORD_COUNT > MIN_WORD_COUNT

    def test_valid_styles(self):
        """Valid styles should include expected options."""
        assert "informative" in VALID_STYLES
        assert "casual" in VALID_STYLES
        assert "technical" in VALID_STYLES
