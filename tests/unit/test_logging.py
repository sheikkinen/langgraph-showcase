"""Tests for yamlgraph.utils.logging module.

Covers:
- Structured logging setup
- JSON format output
- Human-readable format
- Logger configuration from env
"""

import json
import logging
import os
from unittest.mock import patch

import pytest

from yamlgraph.utils.logging import (
    StructuredFormatter,
    get_logger,
    setup_logging,
)


class TestStructuredFormatter:
    """Tests for StructuredFormatter class."""

    @pytest.mark.req("REQ-YG-046")
    def test_human_readable_format(self) -> None:
        """Test human-readable output format (default)."""
        formatter = StructuredFormatter(use_json=False)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)

        assert "[INFO]" in output
        assert "test.logger" in output
        assert "Test message" in output

    @pytest.mark.req("REQ-YG-046")
    def test_json_format(self) -> None:
        """Test JSON output format."""
        formatter = StructuredFormatter(use_json=True)
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)

        # Should be valid JSON
        data = json.loads(output)
        assert data["level"] == "WARNING"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Warning message"
        assert "timestamp" in data

    @pytest.mark.req("REQ-YG-046")
    def test_json_format_with_exception(self) -> None:
        """Test JSON format includes exception info."""
        formatter = StructuredFormatter(use_json=True)
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
            output = formatter.format(record)

        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "Test error" in data["exception"]

    @pytest.mark.req("REQ-YG-046")
    def test_human_format_with_exception(self) -> None:
        """Test human-readable format includes exception."""
        formatter = StructuredFormatter(use_json=False)
        try:
            raise RuntimeError("Runtime failure")
        except RuntimeError:
            import sys

            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
            output = formatter.format(record)

        assert "Error occurred" in output
        assert "RuntimeError" in output
        assert "Runtime failure" in output


class TestSetupLogging:
    """Tests for setup_logging function."""

    @pytest.mark.req("REQ-YG-046")
    def test_default_level_is_info(self) -> None:
        """Test default log level is INFO."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear LOG_LEVEL if set
            os.environ.pop("LOG_LEVEL", None)
            os.environ.pop("LOG_FORMAT", None)

            logger = setup_logging()
            assert logger.level == logging.INFO

    @pytest.mark.req("REQ-YG-046")
    def test_level_from_env(self) -> None:
        """Test log level from LOG_LEVEL env var."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            logger = setup_logging()
            assert logger.level == logging.DEBUG

    @pytest.mark.req("REQ-YG-046")
    def test_level_from_parameter(self) -> None:
        """Test log level from parameter overrides env."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            logger = setup_logging(level="WARNING")
            assert logger.level == logging.WARNING

    @pytest.mark.req("REQ-YG-046")
    def test_json_format_from_env(self) -> None:
        """Test JSON format from LOG_FORMAT env var."""
        with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
            logger = setup_logging()
            handler = logger.handlers[0]
            assert isinstance(handler.formatter, StructuredFormatter)
            assert handler.formatter.use_json is True

    @pytest.mark.req("REQ-YG-046")
    def test_json_format_from_parameter(self) -> None:
        """Test JSON format from parameter."""
        logger = setup_logging(use_json=True)
        handler = logger.handlers[0]
        assert handler.formatter.use_json is True

    @pytest.mark.req("REQ-YG-046")
    def test_removes_existing_handlers(self) -> None:
        """Test that setup clears existing handlers."""
        # Add a dummy handler
        test_logger = logging.getLogger("yamlgraph")
        test_logger.addHandler(logging.StreamHandler())

        # Setup should clear and add exactly one handler
        logger = setup_logging()
        assert len(logger.handlers) == 1

    @pytest.mark.req("REQ-YG-046")
    def test_logger_does_not_propagate(self) -> None:
        """Test that logger doesn't propagate to root."""
        logger = setup_logging()
        assert logger.propagate is False


class TestGetLogger:
    """Tests for get_logger function."""

    @pytest.mark.req("REQ-YG-046")
    def test_returns_logger_instance(self) -> None:
        """Test get_logger returns a Logger."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)

    @pytest.mark.req("REQ-YG-046")
    def test_logger_name_preserved(self) -> None:
        """Test logger name matches input."""
        logger = get_logger("my.custom.module")
        assert logger.name == "my.custom.module"

    @pytest.mark.req("REQ-YG-046")
    def test_child_logger_inherits_config(self) -> None:
        """Test child loggers inherit yamlgraph config."""
        # Setup parent
        setup_logging(level="DEBUG")

        # Get child logger
        child = get_logger("yamlgraph.test.child")

        # Child should inherit effective level
        assert child.getEffectiveLevel() == logging.DEBUG
