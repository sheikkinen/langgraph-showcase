"""Text chunking using LLM-identified markers.

Strategy:
1. LLM identifies exact boundary strings (semantic understanding)
2. Python splits using those strings (reliable string ops)
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk with context."""

    index: int
    title: str
    text: str
    context_before: str
    context_after: str
    char_count: int

    def to_dict(self) -> dict:
        """Convert to dictionary for state serialization."""
        return {
            "index": self.index,
            "title": self.title,
            "text": self.text,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "char_count": self.char_count,
        }


def get_map_result(item: dict | None) -> object | None:
    """Extract result from map node output.

    Map nodes store results with keys like '_map_<node_name>_sub'.
    This function finds and returns that result without hardcoding the key.

    Args:
        item: A single item from a map node's collected output

    Returns:
        The nested result object (Pydantic model or dict), or None
    """
    if not isinstance(item, dict):
        return None

    for key, value in item.items():
        if key.startswith("_map_") and key.endswith("_sub"):
            return value

    return None


def split_by_markers(state: dict, context_chars: int = 300) -> dict:
    """Split text using LLM-identified chapter markers.

    Expects state to contain:
    - source_text: The full text to split
    - chapter_markers: Result from identify_chapters LLM node
      - markers: list of {marker: str, title: str}

    Args:
        state: Pipeline state with source_text and chapter_markers
        context_chars: Characters of overlap for context

    Returns:
        dict with 'chunks' list
    """
    text = state.get("source_text", "")
    markers_result = state.get("chapter_markers", {})

    if not text or not text.strip():
        return {"chunks": []}

    # Extract markers from LLM result (handle Pydantic model or dict)
    if hasattr(markers_result, "markers"):
        markers = markers_result.markers or []
    elif isinstance(markers_result, dict):
        markers = markers_result.get("markers", [])
    else:
        markers = []

    # Build list of split points
    split_points: list[tuple[int, str]] = []  # (position, title)

    for m in markers:
        if isinstance(m, dict):
            marker_text = m.get("marker", "")
            title = m.get("title", "Section")
        elif hasattr(m, "marker"):
            marker_text = m.marker
            title = getattr(m, "title", "Section")
        else:
            continue

        if not marker_text or len(marker_text) < 10:
            continue

        # Find marker in text (normalize whitespace for matching)
        pos = text.find(marker_text)

        # If not found, try with normalized whitespace
        if pos < 0:
            import re

            normalized_text = re.sub(r"\s+", " ", text)
            normalized_marker = re.sub(r"\s+", " ", marker_text)
            pos_normalized = normalized_text.find(normalized_marker)
            if pos_normalized >= 0:
                pos = pos_normalized

        if pos > 0:  # Don't split at position 0
            split_points.append((pos, title))

    # Sort by position
    split_points.sort(key=lambda x: x[0])

    # If no valid markers found, return single chunk
    if not split_points:
        return {
            "chunks": [
                Chunk(
                    index=0,
                    title="Full Document",
                    text=text.strip(),
                    context_before="",
                    context_after="",
                    char_count=len(text.strip()),
                ).to_dict()
            ]
        }

    # Split text at marker positions
    chunks = []
    prev_pos = 0
    prev_title = "Introduction"

    for _i, (pos, title) in enumerate(split_points):
        chunk_text = text[prev_pos:pos].strip()
        if chunk_text:
            # Context from previous chunk
            ctx_before = ""
            if chunks:
                prev_text = chunks[-1]["text"]
                ctx_before = (
                    prev_text[-context_chars:]
                    if len(prev_text) > context_chars
                    else prev_text
                )

            # Context for next chunk (lookahead)
            next_text = text[pos : pos + context_chars]

            chunks.append(
                Chunk(
                    index=len(chunks),
                    title=prev_title,
                    text=chunk_text,
                    context_before=ctx_before,
                    context_after=next_text,
                    char_count=len(chunk_text),
                ).to_dict()
            )

        prev_pos = pos
        prev_title = title

    # Final chunk
    final_text = text[prev_pos:].strip()
    if final_text:
        ctx_before = ""
        if chunks:
            prev_text = chunks[-1]["text"]
            ctx_before = (
                prev_text[-context_chars:]
                if len(prev_text) > context_chars
                else prev_text
            )

        chunks.append(
            Chunk(
                index=len(chunks),
                title=prev_title,
                text=final_text,
                context_before=ctx_before,
                context_after="",
                char_count=len(final_text),
            ).to_dict()
        )

    return {"chunks": chunks}


def merge_terms(state: dict) -> dict:
    """Merge glossary terms from multiple extractions.

    Args:
        state: Must contain 'term_extractions' list and optionally 'glossary'

    Returns:
        dict with updated 'glossary'
    """
    import json

    extractions = state.get("term_extractions", []) or []
    existing = state.get("glossary", {}) or {}

    # Handle string glossary from CLI
    if isinstance(existing, str):
        try:
            existing = json.loads(existing) if existing.strip() else {}
        except json.JSONDecodeError:
            existing = {}

    merged = dict(existing)

    for extraction in extractions:
        # Handle map node output structure
        term_result = get_map_result(extraction)
        if term_result is None:
            continue

        # Handle Pydantic model or dict
        terms = getattr(term_result, "terms", None)
        if terms is None and isinstance(term_result, dict):
            terms = term_result.get("terms", [])
        if not terms:
            continue

        for term in terms:
            if isinstance(term, dict):
                source = term.get("source_term", "")
                translation = term.get("translation", "")
            elif hasattr(term, "source_term"):
                source = term.source_term
                translation = getattr(term, "translation", "")
            else:
                continue

            if source and translation and source not in merged:
                merged[source] = translation

    return {"glossary": merged}


def check_scores(state: dict, threshold: float = 0.8) -> dict:
    """Check quality scores and flag chunks below threshold.

    Args:
        state: Must contain 'proofread_chunks' list
        threshold: Minimum acceptable quality score

    Returns:
        dict with 'flagged_chunks' list and 'needs_review' bool
    """
    proofread = state.get("proofread_chunks", []) or []
    flagged = []

    for i, chunk in enumerate(proofread):
        # Extract proofread result from map node output
        result = get_map_result(chunk)
        if result is None:
            continue

        # Handle Pydantic model or dict
        if hasattr(result, "quality_score"):
            score = result.quality_score
            approved = result.approved
        elif isinstance(result, dict):
            score = result.get("quality_score", 1.0)
            approved = result.get("approved", True)
        else:
            continue

        if score < threshold or not approved:
            flagged.append({"index": i, "score": score, "approved": approved})

    return {
        "flagged_chunks": flagged,
        "needs_review": len(flagged) > 0,
    }


def join_chunks(state: dict) -> dict:
    """Reassemble translated chunks into final text.

    Args:
        state: Contains 'proofread_chunks' and optionally 'reviewed_chunks'

    Returns:
        dict with 'final_text'
    """
    proofread_chunks = state.get("proofread_chunks", []) or []
    reviewed_chunks = state.get("reviewed_chunks", {}) or {}

    final_parts: list[str] = []

    for i, chunk in enumerate(proofread_chunks):
        str_idx = str(i)

        # Priority 1: Human-reviewed version
        if str_idx in reviewed_chunks:
            final_parts.append(reviewed_chunks[str_idx])
            continue

        # Extract proofread result from map node output
        result = get_map_result(chunk)

        if result is not None:
            # Get corrected_text from Pydantic model or dict
            if hasattr(result, "corrected_text"):
                final_parts.append(result.corrected_text)
            elif isinstance(result, dict) and "corrected_text" in result:
                final_parts.append(result["corrected_text"])

    return {"final_text": "\n\n".join(final_parts)}
