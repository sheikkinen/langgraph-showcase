"""Paragraph merger tool for OCR cleanup pipeline.

Merges paragraphs spanning page boundaries and aggregates corrections.
"""

from __future__ import annotations

from collections import Counter


def get_map_result(item: dict | None) -> dict | None:
    """Extract result from map node output.

    Map nodes store results with keys like '_map_<node_name>_sub'.
    """
    if not isinstance(item, dict):
        return None

    for key, value in item.items():
        if key.startswith("_map_") and key.endswith("_sub"):
            return value

    return None


def merge_paragraphs(cleaned_pages: list[dict]) -> dict:
    """Merge paragraphs from cleaned pages, joining those that span pages.

    Args:
        cleaned_pages: List of cleaned page dicts from LLM, each containing:
            - page_num: int
            - paragraphs: list of {text, starts_mid_sentence, ends_mid_sentence}
            - corrections: list of {original, corrected, type}
            - is_chapter_start: bool (optional)
            - chapter_title: str | None (optional)

    Returns:
        dict with keys:
            - paragraphs: list of merged {text, start_page, end_page}
            - corrections: list of all corrections
            - chapters: list of {title, start_page}
            - stats: statistics dict
    """
    all_paragraphs = []
    all_corrections = []
    chapters = []
    pending_text = ""
    pending_start_page = None

    for page in cleaned_pages:
        page_num = page.get("page_num", 0)
        paragraphs = page.get("paragraphs") or []
        corrections = page.get("corrections") or []
        all_corrections.extend(corrections)

        # Track chapter starts
        if page.get("is_chapter_start"):
            chapters.append(
                {
                    "title": page.get("chapter_title"),
                    "start_page": page_num,
                }
            )

        for para in paragraphs:
            # Handle different key names from LLM (prefer cleaned over original)
            text = (
                para.get("cleaned_text")
                or para.get("cleaned")
                or para.get("text")
                or para.get("original_text")
                or para.get("original")
                or ""
            )
            starts_mid = para.get("starts_mid_sentence", False) or para.get(
                "continues_from_previous_page", False
            )
            ends_mid = para.get("ends_mid_sentence", False) or para.get(
                "continues_to_next_page", False
            )

            # Join with pending text from previous page
            if pending_text and starts_mid:
                text = pending_text + " " + text
                # Keep the original start page
            elif pending_text:
                # Previous wasn't continued, flush it
                all_paragraphs.append(
                    {
                        "text": pending_text,
                        "start_page": pending_start_page,
                        "end_page": pending_start_page,
                    }
                )
                pending_text = ""
                pending_start_page = None

            # Check if this continues to next page
            if ends_mid:
                pending_text = text
                if pending_start_page is None:
                    pending_start_page = page_num
            else:
                start_page = pending_start_page if pending_start_page else page_num
                all_paragraphs.append(
                    {
                        "text": text,
                        "start_page": start_page,
                        "end_page": page_num,
                    }
                )
                pending_text = ""
                pending_start_page = None

    # Flush any remaining pending text
    if pending_text:
        all_paragraphs.append(
            {
                "text": pending_text,
                "start_page": pending_start_page or cleaned_pages[-1]["page_num"],
                "end_page": cleaned_pages[-1]["page_num"],
            }
        )

    # Generate stats
    corrections_by_type = Counter(c.get("type", "unknown") for c in all_corrections)

    stats = {
        "total_pages": len(cleaned_pages),
        "total_paragraphs": len(all_paragraphs),
        "total_corrections": len(all_corrections),
        "corrections_by_type": dict(corrections_by_type),
    }

    return {
        "paragraphs": all_paragraphs,
        "corrections": all_corrections,
        "chapters": chapters,
        "stats": stats,
    }


def merge_paragraphs_node(state: dict) -> dict:
    """Node wrapper for merge_paragraphs.

    Reads map_results from state (output of map node).
    Extracts actual page data from map node's nested structure.
    """
    raw_results = state.get("map_results", [])

    # Extract actual page data from map node structure
    cleaned_pages = []
    for item in raw_results:
        page_data = get_map_result(item)

        if page_data is not None:
            # Handle Pydantic model or dict
            if hasattr(page_data, "model_dump"):
                page_data = page_data.model_dump()
            elif hasattr(page_data, "dict"):
                page_data = page_data.dict()
            elif isinstance(page_data, str):
                # Skip string representation (shouldn't happen normally)
                continue

            # Add page_num from _map_index if not present
            if isinstance(page_data, dict) and "page_num" not in page_data:
                page_data["page_num"] = item.get("_map_index", 0) + 1

            if isinstance(page_data, dict):
                cleaned_pages.append(page_data)

    return merge_paragraphs(cleaned_pages)
