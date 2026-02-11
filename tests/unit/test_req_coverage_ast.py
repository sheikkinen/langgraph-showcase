"""Tests for AST-based import fallback in req_coverage.py.

When coverage DB has no data for a test, fall back to parsing
``from yamlgraph.X.Y import Z`` statements to resolve implementation files.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

# Add scripts/ to path so we can import req_coverage directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
from req_coverage import _extract_imports_from_test  # noqa: E402


@pytest.mark.req("REQ-YG-063")
class TestExtractImportsFromTest:
    """Test AST import extraction for coverage fallback."""

    def test_module_level_import_from(self, tmp_path: Path) -> None:
        """from yamlgraph.utils.llm_factory import create_llm → yamlgraph/utils/llm_factory.py."""
        src = textwrap.dedent("""\
            from yamlgraph.utils.llm_factory import create_llm

            def test_something():
                assert create_llm is not None
        """)
        f = tmp_path / "test_example.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_example::test_something")
        assert "yamlgraph/utils/llm_factory.py" in result

    def test_inline_import_in_function(self, tmp_path: Path) -> None:
        """Import inside test function body is captured."""
        src = textwrap.dedent("""\
            def test_inline():
                from yamlgraph.models.schemas import GenericReport
                assert GenericReport is not None
        """)
        f = tmp_path / "test_inline.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_inline::test_inline")
        assert "yamlgraph/models/schemas.py" in result

    def test_class_scoped_test(self, tmp_path: Path) -> None:
        """Class::method key resolves imports from both class body and module level."""
        src = textwrap.dedent("""\
            from yamlgraph.config import PACKAGE_ROOT

            class TestFoo:
                def test_bar(self):
                    assert PACKAGE_ROOT
        """)
        f = tmp_path / "test_cls.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_cls::TestFoo::test_bar")
        assert "yamlgraph/config.py" in result

    def test_ignores_non_yamlgraph_imports(self, tmp_path: Path) -> None:
        """Only yamlgraph imports are returned."""
        src = textwrap.dedent("""\
            import os
            from pathlib import Path
            from yamlgraph.constants import MAX_ITEMS

            def test_const():
                assert MAX_ITEMS > 0
        """)
        f = tmp_path / "test_filter.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_filter::test_const")
        assert result == {"yamlgraph/constants.py"}

    def test_import_yamlgraph_dot_module(self, tmp_path: Path) -> None:
        """import yamlgraph.cli → yamlgraph/cli/__init__.py."""
        src = textwrap.dedent("""\
            import yamlgraph.cli

            def test_cli():
                assert yamlgraph.cli is not None
        """)
        f = tmp_path / "test_import.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_import::test_cli")
        assert "yamlgraph/cli/__init__.py" in result

    def test_multiple_imports_aggregated(self, tmp_path: Path) -> None:
        """Multiple yamlgraph imports produce union of files."""
        src = textwrap.dedent("""\
            from yamlgraph.config import PACKAGE_ROOT
            from yamlgraph.constants import MAX_ITEMS

            def test_multi():
                pass
        """)
        f = tmp_path / "test_multi.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_multi::test_multi")
        assert "yamlgraph/config.py" in result
        assert "yamlgraph/constants.py" in result

    def test_empty_test_returns_empty(self, tmp_path: Path) -> None:
        """Test with no yamlgraph imports returns empty set."""
        src = textwrap.dedent("""\
            def test_noop():
                pass
        """)
        f = tmp_path / "test_empty.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_empty::test_noop")
        assert result == set()

    def test_mock_patch_target_resolved(self, tmp_path: Path) -> None:
        """mock.patch('yamlgraph.foo.bar.func') → yamlgraph/foo/bar.py."""
        src = textwrap.dedent("""\
            from unittest.mock import patch

            class TestMock:
                @patch("yamlgraph.utils.llm_factory.create_llm")
                def test_with_mock(self, mock_llm):
                    pass
        """)
        f = tmp_path / "test_mock.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_mock::TestMock::test_with_mock")
        assert "yamlgraph/utils/llm_factory.py" in result

    def test_function_level_import_preferred(self, tmp_path: Path) -> None:
        """When test key has a function, its inline imports are included."""
        src = textwrap.dedent("""\
            from yamlgraph.config import PACKAGE_ROOT

            class TestSomething:
                def test_specific(self):
                    from yamlgraph.executor import execute_prompt
                    assert execute_prompt
        """)
        f = tmp_path / "test_pref.py"
        f.write_text(src)
        result = _extract_imports_from_test(
            f, "test_pref::TestSomething::test_specific"
        )
        assert "yamlgraph/config.py" in result
        assert "yamlgraph/executor.py" in result

    def test_subpackage_init(self, tmp_path: Path) -> None:
        """from yamlgraph.cli import main → yamlgraph/cli/__init__.py."""
        src = textwrap.dedent("""\
            from yamlgraph.cli import main

            def test_main():
                assert main
        """)
        f = tmp_path / "test_init.py"
        f.write_text(src)
        result = _extract_imports_from_test(f, "test_init::test_main")
        # Could resolve to yamlgraph/cli/__init__.py or yamlgraph/cli.py
        assert any(p.startswith("yamlgraph/cli") for p in result)
