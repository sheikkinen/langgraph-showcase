"""Tests for yamlgraph.config module."""

import pytest

from yamlgraph.config import (
    DATABASE_PATH,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODELS,
    DEFAULT_TEMPERATURE,
    MAX_TOPIC_LENGTH,
    MAX_WORD_COUNT,
    MIN_WORD_COUNT,
    OUTPUTS_DIR,
    PACKAGE_ROOT,
    PROMPTS_DIR,
    VALID_STYLES,
    WORKING_DIR,
)


class TestPaths:
    """Tests for path configuration."""

    @pytest.mark.req("REQ-YG-043")
    def test_package_root_exists(self):
        """Package root directory should exist."""
        assert PACKAGE_ROOT.exists()
        assert PACKAGE_ROOT.is_dir()

    @pytest.mark.req("REQ-YG-043")
    def test_working_dir_exists(self):
        """Working directory should exist."""
        assert WORKING_DIR.exists()
        assert WORKING_DIR.is_dir()

    @pytest.mark.req("REQ-YG-043")
    def test_prompts_dir_exists(self):
        """Prompts directory should exist."""
        assert PROMPTS_DIR.exists()
        assert PROMPTS_DIR.is_dir()

    @pytest.mark.req("REQ-YG-043")
    def test_prompts_dir_has_yaml_files(self):
        """Prompts directory should contain YAML files."""
        yaml_files = list(PROMPTS_DIR.glob("*.yaml"))
        assert len(yaml_files) > 0

    @pytest.mark.req("REQ-YG-043")
    def test_outputs_dir_path(self):
        """Outputs directory path should be under working dir."""
        assert OUTPUTS_DIR.parent == WORKING_DIR

    def test_database_path(self):
        """Database path should be in outputs directory."""
        assert DATABASE_PATH.parent == OUTPUTS_DIR
        assert DATABASE_PATH.suffix == ".db"


class TestLLMConfig:
    """Tests for LLM configuration."""

    @pytest.mark.req("REQ-YG-043")
    def test_default_models_has_all_providers(self):
        """Default models dict should have all supported providers."""
        assert "anthropic" in DEFAULT_MODELS
        assert "mistral" in DEFAULT_MODELS
        assert "openai" in DEFAULT_MODELS

    @pytest.mark.req("REQ-YG-043")
    def test_default_models_are_strings(self):
        """All default models should be non-empty strings."""
        for provider, model in DEFAULT_MODELS.items():
            assert isinstance(model, str), f"{provider} model should be string"
            assert len(model) > 0, f"{provider} model should not be empty"

    @pytest.mark.req("REQ-YG-043")
    def test_default_temperature_range(self):
        """Default temperature should be in valid range."""
        assert 0.0 <= DEFAULT_TEMPERATURE <= 1.0

    def test_default_max_tokens_positive(self):
        """Max tokens should be positive."""
        assert DEFAULT_MAX_TOKENS > 0


class TestCLIConstraints:
    """Tests for CLI validation constraints."""

    @pytest.mark.req("REQ-YG-043")
    def test_topic_length_constraint(self):
        """Max topic length should be reasonable."""
        assert MAX_TOPIC_LENGTH > 0
        assert MAX_TOPIC_LENGTH <= 10000

    @pytest.mark.req("REQ-YG-043")
    def test_word_count_constraints(self):
        """Word count constraints should be valid."""
        assert MIN_WORD_COUNT > 0
        assert MAX_WORD_COUNT > MIN_WORD_COUNT

    @pytest.mark.req("REQ-YG-043")
    def test_valid_styles(self):
        """Valid styles should include expected options."""
        assert "informative" in VALID_STYLES
        assert "casual" in VALID_STYLES
        assert "technical" in VALID_STYLES
