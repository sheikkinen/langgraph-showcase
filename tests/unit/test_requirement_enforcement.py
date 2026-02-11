"""Test that requirement traceability is enforced at collection time.

This test verifies Commandment #10 and ADR-001 enforcement.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.mark.req("REQ-YG-063")
def test_untagged_test_is_rejected(tmp_path: Path):
    """Verify pytest fails when a test lacks @pytest.mark.req."""
    # Create a test file without @pytest.mark.req
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        textwrap.dedent(
            """
            def test_missing_req_tag():
                '''This test has no @pytest.mark.req tag.'''
                assert True
            """
        )
    )

    # Copy conftest.py to tmp_path so enforcement hook is active
    conftest_src = Path(__file__).parent.parent / "conftest.py"
    conftest_dst = tmp_path / "conftest.py"
    conftest_dst.write_text(conftest_src.read_text())

    # Run pytest via subprocess - should fail at collection
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )

    # Should fail with UsageError (non-zero exit)
    assert result.returncode != 0, "Pytest should reject tests without @pytest.mark.req"
    assert (
        "REQUIREMENT TRACEABILITY VIOLATION" in result.stderr
    ), f"Expected enforcement error message in stderr. Got: {result.stderr}"


@pytest.mark.req("REQ-YG-063")
def test_tagged_test_is_accepted(tmp_path: Path):
    """Verify pytest allows tests with proper @pytest.mark.req."""
    # Create a test file WITH @pytest.mark.req
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        textwrap.dedent(
            """
            import pytest

            @pytest.mark.req("REQ-YG-001")
            def test_with_req_tag():
                '''This test has proper @pytest.mark.req tag.'''
                assert True
            """
        )
    )

    # Copy conftest.py to tmp_path so enforcement hook is active
    conftest_src = Path(__file__).parent.parent / "conftest.py"
    conftest_dst = tmp_path / "conftest.py"
    conftest_dst.write_text(conftest_src.read_text())

    # Run pytest via subprocess - should pass
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )

    # Should succeed (0 exit code)
    assert (
        result.returncode == 0
    ), f"Pytest should accept tests with @pytest.mark.req. Output: {result.stdout}"
