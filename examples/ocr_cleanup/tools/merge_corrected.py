"""Merge manually corrected text with original JSON page information.

Uses fuzzy matching to align corrected paragraphs with original paragraphs
and preserve page attribution.
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def parse_txt_paragraphs(txt_path: Path) -> list[str]:
    """Parse text file into paragraphs (split by blank lines)."""
    txt = txt_path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", txt) if p.strip()]
    # Normalize whitespace within paragraphs (remove line breaks)
    return [re.sub(r"\s+", " ", p) for p in paragraphs]


def load_json_paragraphs(json_path: Path) -> list[dict]:
    """Load paragraphs from JSON file."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return data.get("paragraphs", [])


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_best_matches(
    txt_para: str,
    json_paragraphs: list[dict],
    start_idx: int,
    window: int = 20,
) -> list[tuple[int, float]]:
    """Find best matching JSON paragraphs within a window.

    Returns list of (index, similarity_score) tuples sorted by score descending.
    """
    matches = []
    end_idx = min(start_idx + window, len(json_paragraphs))
    search_start = max(0, start_idx - 5)  # Look back a bit too

    for i in range(search_start, end_idx):
        json_text = json_paragraphs[i]["text"]
        score = similarity(txt_para, json_text)
        matches.append((i, score))

    return sorted(matches, key=lambda x: x[1], reverse=True)


def find_merged_range(
    txt_para: str,
    json_paragraphs: list[dict],
    start_idx: int,
    window: int = 10,
) -> tuple[int, int, float]:
    """Check if txt paragraph is a merge of consecutive JSON paragraphs.

    Returns (start_idx, end_idx, combined_similarity).
    """
    best_range = (start_idx, start_idx, 0.0)

    for length in range(2, min(6, window)):  # Try merging 2-5 paragraphs
        end = start_idx + length
        if end > len(json_paragraphs):
            break

        # Combine consecutive JSON paragraphs
        combined = " ".join(json_paragraphs[i]["text"] for i in range(start_idx, end))
        score = similarity(txt_para, combined)

        if score > best_range[2]:
            best_range = (start_idx, end - 1, score)

    return best_range


def merge_corrected(
    json_path: Path,
    txt_path: Path,
    output_path: Path,
    similarity_threshold: float = 0.6,
) -> dict:
    """Merge corrected text with original JSON page information.

    Args:
        json_path: Path to original final.json
        txt_path: Path to corrected final.txt
        output_path: Path for output final_pages.json
        similarity_threshold: Minimum similarity for confident match

    Returns:
        Result dict with merged paragraphs and stats
    """
    txt_paragraphs = parse_txt_paragraphs(txt_path)
    json_paragraphs = load_json_paragraphs(json_path)

    print(f"📖 TXT paragraphs: {len(txt_paragraphs)}")
    print(f"📄 JSON paragraphs: {len(json_paragraphs)}")

    merged = []
    json_idx = 0  # Track position in JSON paragraphs
    unmatched = []

    for txt_idx, txt_para in enumerate(txt_paragraphs):
        # Try single paragraph match first
        matches = find_best_matches(txt_para, json_paragraphs, json_idx)

        if matches and matches[0][1] >= similarity_threshold:
            # Good single match
            best_idx, score = matches[0]
            json_para = json_paragraphs[best_idx]
            merged.append(
                {
                    "text": txt_para,
                    "start_page": json_para["start_page"],
                    "end_page": json_para["end_page"],
                    "match_score": round(score, 3),
                    "match_type": "single",
                }
            )
            json_idx = best_idx + 1
        else:
            # Try merged paragraph detection
            merge_start, merge_end, merge_score = find_merged_range(
                txt_para, json_paragraphs, json_idx
            )

            if merge_score >= similarity_threshold:
                # This is a merged paragraph
                start_page = json_paragraphs[merge_start]["start_page"]
                end_page = json_paragraphs[merge_end]["end_page"]
                merged.append(
                    {
                        "text": txt_para,
                        "start_page": start_page,
                        "end_page": end_page,
                        "match_score": round(merge_score, 3),
                        "match_type": f"merged_{merge_end - merge_start + 1}",
                    }
                )
                json_idx = merge_end + 1
            else:
                # Low confidence - use best guess with warning
                if matches:
                    best_idx, score = matches[0]
                    json_para = json_paragraphs[best_idx]
                    merged.append(
                        {
                            "text": txt_para,
                            "start_page": json_para["start_page"],
                            "end_page": json_para["end_page"],
                            "match_score": round(score, 3),
                            "match_type": "low_confidence",
                        }
                    )
                    unmatched.append(
                        {
                            "txt_idx": txt_idx,
                            "text_preview": txt_para[:80],
                            "score": round(score, 3),
                        }
                    )
                    json_idx = best_idx + 1
                else:
                    # Fallback: interpolate from neighbors
                    prev_page = merged[-1]["end_page"] if merged else 1
                    merged.append(
                        {
                            "text": txt_para,
                            "start_page": prev_page,
                            "end_page": prev_page,
                            "match_score": 0.0,
                            "match_type": "interpolated",
                        }
                    )
                    unmatched.append(
                        {
                            "txt_idx": txt_idx,
                            "text_preview": txt_para[:80],
                            "score": 0.0,
                        }
                    )

    # Build result
    result = {
        "paragraphs": merged,
        "stats": {
            "total_paragraphs": len(merged),
            "single_matches": sum(1 for p in merged if p["match_type"] == "single"),
            "merged_matches": sum(
                1 for p in merged if p["match_type"].startswith("merged")
            ),
            "low_confidence": sum(
                1 for p in merged if p["match_type"] == "low_confidence"
            ),
            "interpolated": sum(1 for p in merged if p["match_type"] == "interpolated"),
            "avg_score": round(sum(p["match_score"] for p in merged) / len(merged), 3)
            if merged
            else 0,
        },
        "unmatched": unmatched,
    }

    # Save output
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n✅ Saved to {output_path}")
    print(f"📊 Stats: {json.dumps(result['stats'], indent=2)}")

    if unmatched:
        print(f"\n⚠️  {len(unmatched)} low-confidence matches need review")

    return result


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Merge corrected text with JSON")
    parser.add_argument("json_path", type=Path, help="Path to original final.json")
    parser.add_argument("txt_path", type=Path, help="Path to corrected final.txt")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: final_pages.json in same dir)",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=0.6,
        help="Similarity threshold (default: 0.6)",
    )

    args = parser.parse_args()

    output = args.output or args.json_path.parent / "final_pages.json"
    merge_corrected(args.json_path, args.txt_path, output, args.threshold)


if __name__ == "__main__":
    main()
