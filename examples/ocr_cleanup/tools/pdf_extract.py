"""PDF text extraction tool for OCR cleanup pipeline."""

from __future__ import annotations

import subprocess


def extract_pages(
    pdf_path: str,
    start_page: int = 1,
    end_page: int | None = None,
) -> dict:
    """Extract text from PDF page by page.

    Args:
        pdf_path: Path to PDF file
        start_page: First page to extract (1-indexed, default 1)
        end_page: Last page to extract (inclusive, default all)

    Returns:
        dict with keys:
            - pages: list of {page_num, raw_text, prev_last_line}
            - total_pages: total pages in PDF
    """
    pdf_path = str(pdf_path)

    # Get total page count
    result = subprocess.run(
        ["pdfinfo", pdf_path],
        capture_output=True,
        text=True,
    )
    pages_line = [line for line in result.stdout.split("\n") if "Pages:" in line][0]
    total_pages = int(pages_line.split(":")[1].strip())

    # Default end_page to total
    if end_page is None:
        end_page = total_pages

    pages = []
    prev_last_line = ""

    for page_num in range(start_page, end_page + 1):
        result = subprocess.run(
            [
                "pdftotext",
                "-layout",
                "-f",
                str(page_num),
                "-l",
                str(page_num),
                pdf_path,
                "-",
            ],
            capture_output=True,
            text=True,
        )

        raw_text = result.stdout

        pages.append(
            {
                "page_num": page_num,
                "raw_text": raw_text,
                "prev_last_line": prev_last_line,
            }
        )

        # Get last non-empty line for next page context
        lines = [line for line in raw_text.strip().split("\n") if line.strip()]
        prev_last_line = lines[-1] if lines else ""

    return {
        "pages": pages,
        "total_pages": total_pages,
    }


def extract_pages_node(state: dict) -> dict:
    """Node wrapper for extract_pages.

    Reads pdf_path from state, optionally start_page and end_page.
    """
    pdf_path = state["pdf_path"]
    start_page = int(state.get("start_page", 1))
    end_page = state.get("end_page")
    if end_page is not None:
        end_page = int(end_page)

    return extract_pages(pdf_path, start_page=start_page, end_page=end_page)
