"""Python tools for text analysis demo."""


def analyze_text(state: dict) -> dict:
    """Analyze a single text snippet.

    Args:
        state: Must contain 'text' key with string to analyze

    Returns:
        Dict with 'stats' key containing analysis results
    """
    text = state["text"]
    words = text.split()

    return {
        "stats": {
            "char_count": len(text),
            "word_count": len(words),
            "avg_word_len": round(sum(len(w) for w in words) / len(words), 1)
            if words
            else 0,
            "has_question": "?" in text,
        }
    }
