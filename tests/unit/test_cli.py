"""Tests for showcase.cli module."""

import argparse

from yamlgraph.cli.validators import validate_run_args
from yamlgraph.config import MAX_TOPIC_LENGTH, MAX_WORD_COUNT, MIN_WORD_COUNT


class TestValidateRunArgs:
    """Tests for validate_run_args function."""

    def _create_args(self, topic="test topic", word_count=300, style="informative"):
        """Helper to create args namespace."""
        return argparse.Namespace(
            topic=topic,
            word_count=word_count,
            style=style,
        )

    def test_valid_args(self):
        """Valid arguments should pass validation."""
        args = self._create_args()
        assert validate_run_args(args) is True

    def test_empty_topic(self):
        """Empty topic should fail validation."""
        args = self._create_args(topic="")
        assert validate_run_args(args) is False

    def test_whitespace_only_topic(self):
        """Whitespace-only topic should fail validation."""
        args = self._create_args(topic="   ")
        assert validate_run_args(args) is False

    def test_topic_too_long(self):
        """Topic exceeding max length should be truncated with warning."""
        long_topic = "x" * (MAX_TOPIC_LENGTH + 100)
        args = self._create_args(topic=long_topic)
        # Should pass but truncate the topic
        assert validate_run_args(args) is True
        assert len(args.topic) == MAX_TOPIC_LENGTH

    def test_topic_at_max_length(self):
        """Topic at max length should pass validation."""
        max_topic = "x" * MAX_TOPIC_LENGTH
        args = self._create_args(topic=max_topic)
        assert validate_run_args(args) is True

    def test_word_count_too_low(self):
        """Word count below minimum should fail validation."""
        args = self._create_args(word_count=MIN_WORD_COUNT - 1)
        assert validate_run_args(args) is False

    def test_word_count_too_high(self):
        """Word count above maximum should fail validation."""
        args = self._create_args(word_count=MAX_WORD_COUNT + 1)
        assert validate_run_args(args) is False

    def test_word_count_at_min(self):
        """Word count at minimum should pass validation."""
        args = self._create_args(word_count=MIN_WORD_COUNT)
        assert validate_run_args(args) is True

    def test_word_count_at_max(self):
        """Word count at maximum should pass validation."""
        args = self._create_args(word_count=MAX_WORD_COUNT)
        assert validate_run_args(args) is True


class TestFormatResult:
    """Tests for generic result formatting."""

    def test_format_result_with_any_pydantic_model(self, capsys):
        """CLI should format any Pydantic model, not just known ones."""
        from pydantic import BaseModel

        from yamlgraph.cli.commands import _format_result

        class CustomResult(BaseModel):
            title: str
            score: float
            items: list[str]

        result = {
            "current_step": "done",
            "custom": CustomResult(title="Test Title", score=0.95, items=["a", "b"]),
        }

        _format_result(result)
        captured = capsys.readouterr()
        assert "Test Title" in captured.out
        assert "0.95" in captured.out

    def test_format_result_skips_internal_keys(self, capsys):
        """Internal keys should be skipped."""
        from yamlgraph.cli.commands import _format_result

        result = {
            "current_step": "done",
            "_route": "positive",
            "_loop_counts": {"draft": 2},
            "response": "Hello!",
        }

        _format_result(result)
        captured = capsys.readouterr()
        assert "_route" not in captured.out
        assert "_loop_counts" not in captured.out
        assert "Hello!" in captured.out

    def test_format_result_truncates_long_strings(self, capsys):
        """Long strings should be truncated."""
        from yamlgraph.cli.commands import _format_result

        long_text = "x" * 500
        result = {"summary": long_text}

        _format_result(result)
        captured = capsys.readouterr()
        assert "..." in captured.out
        assert len(captured.out) < 400  # Truncated
