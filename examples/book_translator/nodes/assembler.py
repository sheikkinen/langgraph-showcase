"""Chunk reassembly for final output."""


def join_chunks(state: dict) -> dict:
    """Reassemble proofread chunks into final text.

    Priority for each chunk:
    1. Human-reviewed version (from reviewed_chunks)
    2. Corrected text from proofreading
    3. Original text from proofreading
    4. Fallback to translations

    Args:
        state: Must contain 'proofread_chunks' list
               Optional 'reviewed_chunks' dict (index -> corrected text)
               Optional 'translations' list (fallback)

    Returns:
        dict with 'final_text' containing reassembled book
    """
    proofread_chunks = state.get("proofread_chunks", []) or []
    reviewed_chunks = state.get("reviewed_chunks", {}) or {}
    translations = state.get("translations", []) or []

    final_parts: list[str] = []

    for i, chunk in enumerate(proofread_chunks):
        # Priority 1: Human-reviewed version
        str_idx = str(i)
        if str_idx in reviewed_chunks:
            final_parts.append(reviewed_chunks[str_idx])
            continue

        # Extract the actual proofread result from map node output
        proofread_result = None
        if chunk is not None and isinstance(chunk, dict):
            # Map nodes wrap results in _map_<name>_sub key
            proofread_result = chunk.get("_map_proofread_all_sub")

        # Priority 2 & 3: Proofread result
        if proofread_result is not None:
            # Handle Pydantic model or dict
            if hasattr(proofread_result, "corrected_text"):
                final_parts.append(proofread_result.corrected_text)
                continue
            if isinstance(proofread_result, dict):
                if "corrected_text" in proofread_result:
                    final_parts.append(proofread_result["corrected_text"])
                    continue
                if "text" in proofread_result:
                    final_parts.append(proofread_result["text"])
                    continue

        # Priority 4: Fallback to original translation
        if i < len(translations):
            translation_chunk = translations[i]
            translation_result = None
            if isinstance(translation_chunk, dict):
                translation_result = translation_chunk.get("_map_translate_all_sub")

            if translation_result is not None:
                if hasattr(translation_result, "text"):
                    final_parts.append(translation_result.text)
                    continue
                if (
                    isinstance(translation_result, dict)
                    and "text" in translation_result
                ):
                    final_parts.append(translation_result["text"])
                    continue
            elif isinstance(translation_chunk, str):
                final_parts.append(translation_chunk)
                continue

    return {"final_text": "\n\n".join(final_parts)}
