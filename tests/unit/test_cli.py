"""Tests for showcase.cli module."""

import argparse


from showcase.cli import validate_run_args
from showcase.config import MAX_TOPIC_LENGTH, MIN_WORD_COUNT, MAX_WORD_COUNT


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
