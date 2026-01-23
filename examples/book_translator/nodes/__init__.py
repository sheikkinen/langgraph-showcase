# Book Translator Nodes
"""Python nodes for book translation pipeline."""

# Lazy imports to avoid circular dependencies during testing
__all__ = [
    "split_by_chapters",
    "split_by_size",
    "merge_terms",
    "check_scores",
    "join_chunks",
]


def __getattr__(name: str):
    """Lazy import pattern for nodes."""
    if name in ("split_by_chapters", "split_by_size"):
        from .splitter import split_by_chapters, split_by_size

        return split_by_chapters if name == "split_by_chapters" else split_by_size
    elif name == "merge_terms":
        from .glossary import merge_terms

        return merge_terms
    elif name == "check_scores":
        from .quality import check_scores

        return check_scores
    elif name == "join_chunks":
        from .assembler import join_chunks

        return join_chunks
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
