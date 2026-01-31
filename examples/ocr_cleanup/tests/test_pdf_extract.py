"""Tests for PDF extraction tool."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestExtractPages:
    """Tests for extract_pages function."""

    def test_extract_pages_returns_page_list(self) -> None:
        """Extract pages returns list with page_num and raw_text."""
        from examples.ocr_cleanup.tools.pdf_extract import extract_pages

        with patch("subprocess.run") as mock_run:
            # Mock pdfinfo
            mock_run.return_value = MagicMock(
                stdout="Pages:          3\n",
                returncode=0,
            )

            # We need to handle multiple calls
            def run_side_effect(*args, **kwargs):
                cmd = args[0]
                if "pdfinfo" in cmd:
                    return MagicMock(stdout="Pages:          3\n", returncode=0)
                elif "pdftotext" in cmd:
                    page_num = cmd[cmd.index("-f") + 1]
                    return MagicMock(
                        stdout=f"Page {page_num} content\nLine 2\n",
                        returncode=0,
                    )
                return MagicMock(stdout="", returncode=0)

            mock_run.side_effect = run_side_effect

            result = extract_pages("/fake/path.pdf")

            assert "pages" in result
            assert "total_pages" in result
            assert result["total_pages"] == 3
            assert len(result["pages"]) == 3

    def test_page_structure_has_required_fields(self) -> None:
        """Each page has page_num, raw_text, prev_last_line."""
        from examples.ocr_cleanup.tools.pdf_extract import extract_pages

        with patch("subprocess.run") as mock_run:

            def run_side_effect(*args, **kwargs):
                cmd = args[0]
                if "pdfinfo" in cmd:
                    return MagicMock(stdout="Pages:          2\n", returncode=0)
                elif "pdftotext" in cmd:
                    page_num = int(cmd[cmd.index("-f") + 1])
                    return MagicMock(
                        stdout=f"Page {page_num} line 1\nPage {page_num} line 2\n",
                        returncode=0,
                    )
                return MagicMock(stdout="", returncode=0)

            mock_run.side_effect = run_side_effect

            result = extract_pages("/fake/path.pdf")
            page = result["pages"][0]

            assert "page_num" in page
            assert "raw_text" in page
            assert "prev_last_line" in page

    def test_prev_last_line_carries_forward(self) -> None:
        """Second page gets last line from first page."""
        from examples.ocr_cleanup.tools.pdf_extract import extract_pages

        with patch("subprocess.run") as mock_run:

            def run_side_effect(*args, **kwargs):
                cmd = args[0]
                if "pdfinfo" in cmd:
                    return MagicMock(stdout="Pages:          2\n", returncode=0)
                elif "pdftotext" in cmd:
                    page_num = int(cmd[cmd.index("-f") + 1])
                    if page_num == 1:
                        return MagicMock(
                            stdout="First page\nEnds with this line\n",
                            returncode=0,
                        )
                    else:
                        return MagicMock(
                            stdout="Second page content\n",
                            returncode=0,
                        )
                return MagicMock(stdout="", returncode=0)

            mock_run.side_effect = run_side_effect

            result = extract_pages("/fake/path.pdf")

            assert result["pages"][0]["prev_last_line"] == ""
            assert result["pages"][1]["prev_last_line"] == "Ends with this line"

    def test_extract_pages_node_wrapper(self) -> None:
        """Node wrapper extracts pdf_path from state."""
        from examples.ocr_cleanup.tools.pdf_extract import extract_pages_node

        with patch("examples.ocr_cleanup.tools.pdf_extract.extract_pages") as mock:
            mock.return_value = {"pages": [], "total_pages": 0}

            state = {"pdf_path": "/some/path.pdf"}
            _ = extract_pages_node(state)

            mock.assert_called_once_with("/some/path.pdf", start_page=1, end_page=None)

    def test_extract_with_start_page(self) -> None:
        """Start page skips front matter."""
        from examples.ocr_cleanup.tools.pdf_extract import extract_pages

        with patch("subprocess.run") as mock_run:

            def run_side_effect(*args, **kwargs):
                cmd = args[0]
                if "pdfinfo" in cmd:
                    return MagicMock(stdout="Pages:          10\n", returncode=0)
                elif "pdftotext" in cmd:
                    page_num = int(cmd[cmd.index("-f") + 1])
                    return MagicMock(
                        stdout=f"Page {page_num}\n",
                        returncode=0,
                    )
                return MagicMock(stdout="", returncode=0)

            mock_run.side_effect = run_side_effect

            result = extract_pages("/fake/path.pdf", start_page=5)

            assert result["pages"][0]["page_num"] == 5
            assert len(result["pages"]) == 6  # Pages 5-10


class TestExtractPagesIntegration:
    """Integration tests with real PDF (requires tmp/ file)."""

    @pytest.fixture
    def sample_pdf(self) -> Path:
        """Path to sample PDF if exists."""
        pdf_path = Path("tmp/Yhdeksän_miehen_saappaat_Pentti_Haanpää_01_01_1945.pdf")
        if not pdf_path.exists():
            pytest.skip("Sample PDF not available")
        return pdf_path

    def test_real_pdf_extraction(self, sample_pdf: Path) -> None:
        """Test with real PDF file."""
        from examples.ocr_cleanup.tools.pdf_extract import extract_pages

        result = extract_pages(str(sample_pdf), start_page=9, end_page=11)

        assert result["total_pages"] == 184
        assert len(result["pages"]) == 3  # Pages 9, 10, 11
        assert result["pages"][0]["page_num"] == 9
        assert "Saapasparit" in result["pages"][0]["raw_text"]
