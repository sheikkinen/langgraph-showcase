"""Tests for example discovery tools."""

from pathlib import Path

from yamlgraph.tools.analysis.example_tools import (
    find_error_handling,
    find_example,
)

# ============================================================================
# find_example tests
# ============================================================================


class TestFindExample:
    """Tests for find_example."""

    def test_finds_function_usage(self, tmp_path: Path):
        """Find usage examples of a function."""
        # Create a source file
        src = tmp_path / "mymodule.py"
        src.write_text('''
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"
''')
        # Create a file that uses it
        user = tmp_path / "main.py"
        user.write_text("""
from mymodule import greet

def run():
    result = greet("World")
    print(result)
""")
        result = find_example("greet", str(tmp_path))

        assert "examples" in result
        assert len(result["examples"]) >= 1
        example = result["examples"][0]
        assert "file" in example
        assert "line" in example
        assert "snippet" in example
        assert "greet" in example["snippet"]

    def test_prioritizes_test_files(self, tmp_path: Path):
        """Test files should appear first in examples."""
        # Source
        src = tmp_path / "utils.py"
        src.write_text("def helper(): pass")

        # Regular usage
        main = tmp_path / "main.py"
        main.write_text("from utils import helper\nhelper()")

        # Test usage
        tests = tmp_path / "tests"
        tests.mkdir()
        test_file = tests / "test_utils.py"
        test_file.write_text("""
from utils import helper

def test_helper():
    result = helper()
    assert result is None
""")
        result = find_example("helper", str(tmp_path))

        assert "examples" in result
        # First example should be from test file
        if result["examples"]:
            first = result["examples"][0]
            assert "test" in first["file"].lower()

    def test_limits_max_examples(self, tmp_path: Path):
        """Respects max_examples parameter."""
        src = tmp_path / "funcs.py"
        src.write_text("def foo(): pass")

        for i in range(5):
            f = tmp_path / f"user{i}.py"
            f.write_text(f"from funcs import foo\nfoo()  # usage {i}")

        result = find_example("foo", str(tmp_path), max_examples=2)

        assert "examples" in result
        assert len(result["examples"]) <= 2

    def test_handles_no_examples(self, tmp_path: Path):
        """Returns empty list when no examples found."""
        src = tmp_path / "module.py"
        src.write_text("def unused(): pass")

        result = find_example("unused", str(tmp_path))

        assert "examples" in result
        assert len(result["examples"]) == 0

    def test_handles_missing_project(self):
        """Returns error for missing project path."""
        result = find_example("symbol", "/nonexistent/path")
        assert "error" in result


# ============================================================================
# find_error_handling tests
# ============================================================================


class TestFindErrorHandling:
    """Tests for find_error_handling."""

    def test_finds_exception_types(self, tmp_path: Path):
        """Discovers exception types used in project."""
        src = tmp_path / "handler.py"
        src.write_text("""
try:
    risky_operation()
except ValueError as e:
    print(f"Value error: {e}")
except KeyError:
    pass
except (TypeError, AttributeError):
    pass
""")
        result = find_error_handling(str(tmp_path))

        assert "exceptions" in result
        exceptions = result["exceptions"]
        assert "ValueError" in exceptions
        assert "KeyError" in exceptions

    def test_finds_dict_error_pattern(self, tmp_path: Path):
        """Detects dict-based error returns."""
        src = tmp_path / "tool.py"
        src.write_text("""
def process(data):
    if not data:
        return {"error": "No data provided"}
    try:
        result = compute(data)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
""")
        result = find_error_handling(str(tmp_path))

        assert "patterns" in result
        patterns = result["patterns"]
        assert "dict_error" in patterns or any("dict" in p.lower() for p in patterns)

    def test_finds_logging_patterns(self, tmp_path: Path):
        """Detects error logging patterns."""
        src = tmp_path / "service.py"
        src.write_text("""
import logging

logger = logging.getLogger(__name__)

def do_work():
    try:
        work()
    except Exception as e:
        logger.error(f"Failed: {e}")
        raise
""")
        result = find_error_handling(str(tmp_path))

        assert "logging" in result
        assert result["logging"]["uses_logging"] is True

    def test_handles_no_error_handling(self, tmp_path: Path):
        """Returns empty patterns for code without error handling."""
        src = tmp_path / "simple.py"
        src.write_text("x = 1 + 1\nprint(x)")

        result = find_error_handling(str(tmp_path))

        assert "exceptions" in result
        assert len(result["exceptions"]) == 0

    def test_handles_missing_project(self):
        """Returns error for missing project path."""
        result = find_error_handling("/nonexistent/path")
        assert "error" in result
