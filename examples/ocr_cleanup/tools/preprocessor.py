"""Text preprocessing tool for OCR cleanup pipeline.

Normalizes quotes and filters unexpected characters before LLM processing.
"""

from __future__ import annotations

import re

# Characters allowed in Finnish text
ALLOWED_PATTERN = re.compile(r"[^a-zA-ZäöåüÄÖÅÜ.,;:!?'\"()\-\s…\d\n]")

# Quote normalization mappings
QUOTE_MAP = {
    "»": '"',
    "«": '"',
    "„": '"',
    """: '"',
    """: '"',
    "\u2018": "'",  # LEFT SINGLE QUOTATION MARK
    "\u2019": "'",  # RIGHT SINGLE QUOTATION MARK
    "‚": "'",  # U+201A SINGLE LOW-9 QUOTATION MARK
}


def normalize_quotes(text: str) -> str:
    """Replace various quote characters with standard ASCII quotes."""
    for old, new in QUOTE_MAP.items():
        text = text.replace(old, new)
    return text


def filter_unexpected_chars(text: str) -> str:
    """Remove characters not in the allowed set."""
    return ALLOWED_PATTERN.sub("", text)


def preprocess_text(text: str) -> str:
    """Apply all preprocessing steps to text.

    1. Normalize quotes to ASCII
    2. Filter unexpected characters
    """
    text = normalize_quotes(text)
    text = filter_unexpected_chars(text)
    return text


def preprocess_pages_node(state: dict) -> dict:
    """Node wrapper for preprocessing pages.

    Applies preprocessing to each page's raw_text before LLM cleanup.
    """
    pages = state.get("pages", [])

    preprocessed = []
    for page in pages:
        preprocessed.append(
            {
                **page,
                "raw_text": preprocess_text(page.get("raw_text", "")),
                "prev_last_line": preprocess_text(page.get("prev_last_line", "")),
            }
        )

    return {"pages": preprocessed}
