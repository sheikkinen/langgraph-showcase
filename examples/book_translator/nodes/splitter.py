"""Text chunking strategies for translation."""

import re
from dataclasses import dataclass
from pathlib import Path


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


def split_by_llm(state: dict, context_chars: int = 500) -> dict:
    """Use LLM to analyze text structure and split intelligently.

    Args:
        state: Must contain 'source_text', optionally 'glossary'
        context_chars: Number of characters to include as context

    Returns:
        dict with 'chunks' key containing list of chunk dicts
    """
    from yamlgraph.executor import execute_prompt

    text = state.get("source_text", "")
    glossary = state.get("glossary", {})
    source_language = state.get("source_language", "unknown")

    if not text or not text.strip():
        return {"chunks": []}

    # Use LLM to analyze structure
    prompt_path = Path(__file__).parent.parent / "prompts" / "analyze_structure.yaml"
    if not prompt_path.exists():
        # Fallback to regex-based splitting
        return split_by_chapters(state, context_chars)

    try:
        analysis = execute_prompt(
            str(prompt_path),
            variables={
                "source_text": text,
                "source_language": source_language,
                "glossary": glossary if isinstance(glossary, dict) else {},
            },
        )

        sections = getattr(analysis, "sections", []) or []
        if not sections or len(sections) < 2:
            return split_by_chapters(state, context_chars)

        # Split text based on LLM-identified markers
        parts = _split_by_markers(text, sections)
        if len(parts) > 1:
            return _build_chunks(parts, context_chars)

    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"LLM split failed, using regex: {e}")

    return split_by_chapters(state, context_chars)


def _split_by_markers(text: str, sections: list) -> list[str]:
    """Split text using LLM-identified section markers.

    Args:
        text: Full text to split
        sections: List of section dicts with start_marker keys

    Returns:
        List of text parts
    """
    parts = []
    remaining = text

    for section in sections:
        if not isinstance(section, dict):
            continue

        marker = section.get("start_marker", "")
        if not marker or len(marker) < 5:
            continue

        # Find the marker in remaining text
        idx = remaining.find(marker)
        if idx > 0:
            # Split at this point
            parts.append(remaining[:idx].strip())
            remaining = remaining[idx:]

    # Add final part
    if remaining.strip():
        parts.append(remaining.strip())

    return [p for p in parts if p]


def split_by_chapters(state: dict, context_chars: int = 500) -> dict:
    """Split text into chapters/sections with surrounding context.

    Supports multiple section markers:
    - Chapter/CHAPTER/Kapitel/Chapitre (numbered chapters)
    - Kertomus/Selostus (Finnish: "Report"/"Description")
    - Major section headers (double newline + title pattern)

    Args:
        state: Must contain 'source_text' key
        context_chars: Number of characters to include as context

    Returns:
        dict with 'chunks' key containing list of chunk dicts
    """
    text = state.get("source_text", "")

    if not text or not text.strip():
        return {"chunks": []}

    # Try multiple splitting strategies in order of specificity

    # 1. Finnish war diary: "Kertomus" (battle report) sections
    if "Kertomus" in text or "Selostus" in text:
        # Split on major section headers (Kertomus = Report, Selostus = Description)
        section_pattern = r"(?=\n\n(?:Kertomus|Selostus|Tarkemmin)[^\n]*\n)"
        parts = re.split(section_pattern, text)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) > 1:
            return _build_chunks(parts, context_chars)

    # 2. Standard chapter markers
    chapter_pattern = r"(?=\n(?:Chapter|CHAPTER|Kapitel|Chapitre|Luku)\s+\d+)"
    parts = re.split(chapter_pattern, text)
    parts = [p for p in parts if p.strip()]

    if len(parts) > 1:
        return _build_chunks(parts, context_chars)

    # 3. If no markers found, split by size (max 4000 chars for optimal translation)
    return split_by_size(state, max_chars=4000, overlap=200)


def _build_chunks(parts: list[str], context_chars: int = 500) -> dict:
    """Build chunk list from text parts with context.

    Args:
        parts: List of text parts to convert to chunks
        context_chars: Number of context characters from adjacent chunks

    Returns:
        dict with 'chunks' key
    """
    chunks = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue

        # Extract title from first line
        lines = part.split("\n")
        title = lines[0].strip() if lines else f"Section {i + 1}"
        # Truncate long titles
        if len(title) > 80:
            title = title[:77] + "..."

        # Get context from adjacent chunks
        context_before = ""
        context_after = ""

        if i > 0:
            prev_text = parts[i - 1].strip()
            context_before = (
                prev_text[-context_chars:]
                if len(prev_text) > context_chars
                else prev_text
            )

        if i < len(parts) - 1:
            next_text = parts[i + 1].strip()
            context_after = (
                next_text[:context_chars]
                if len(next_text) > context_chars
                else next_text
            )

        chunk = Chunk(
            index=len(chunks),
            title=title,
            text=part,
            context_before=context_before,
            context_after=context_after,
            char_count=len(part),
        )
        chunks.append(chunk.to_dict())

    return {"chunks": chunks}


def split_by_size(state: dict, max_chars: int = 5000, overlap: int = 200) -> dict:
    """Split text by character count with overlap for context.

    Splits at paragraph boundaries to preserve semantic units.

    Args:
        state: Must contain 'source_text' key
        max_chars: Maximum characters per chunk (approximate, respects paragraphs)
        overlap: Number of characters to overlap between chunks for context

    Returns:
        dict with 'chunks' key containing list of chunk dicts
    """
    text = state.get("source_text", "")

    if not text or not text.strip():
        return {"chunks": []}

    # Split at paragraph boundaries
    paragraphs = text.split("\n\n")
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return {"chunks": []}

    chunks = []
    current_chunk: list[str] = []
    current_size = 0

    for para in paragraphs:
        # If adding this paragraph exceeds max and we have content, finalize chunk
        if current_size + len(para) > max_chars and current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                {
                    "index": len(chunks),
                    "title": f"Section {len(chunks) + 1}",
                    "text": chunk_text,
                    "context_before": "",  # Filled in second pass
                    "context_after": "",  # Filled in second pass
                    "char_count": len(chunk_text),
                }
            )
            current_chunk = [para]
            current_size = len(para)
        else:
            current_chunk.append(para)
            current_size += len(para)

    # Final chunk
    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        chunks.append(
            {
                "index": len(chunks),
                "title": f"Section {len(chunks) + 1}",
                "text": chunk_text,
                "context_before": "",
                "context_after": "",
                "char_count": len(chunk_text),
            }
        )

    # Second pass: fill in context overlap
    for i, chunk in enumerate(chunks):
        if i > 0:
            prev_text = chunks[i - 1]["text"]
            chunk["context_before"] = (
                prev_text[-overlap:] if len(prev_text) > overlap else prev_text
            )

        if i < len(chunks) - 1:
            next_text = chunks[i + 1]["text"]
            chunk["context_after"] = (
                next_text[:overlap] if len(next_text) > overlap else next_text
            )

    return {"chunks": chunks}
