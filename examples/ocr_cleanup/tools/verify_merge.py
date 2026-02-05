"""Verify merged output: low confidence matches, page coverage, and order."""

import json
import sys


def verify_merge(path: str) -> dict:
    """Verify merged output and return stats."""
    with open(path) as f:
        data = json.load(f)

    paragraphs = data["paragraphs"]
    print(f"Total paragraphs: {len(paragraphs)}")

    # Low confidence matches (< 0.8)
    low_conf = [
        (i, p["match_score"], p.get("match_type", "single"), p["text"][:60])
        for i, p in enumerate(paragraphs)
        if p.get("match_score", 1.0) < 0.8
    ]
    print(f"\n🔍 Low confidence matches (<0.8): {len(low_conf)}")
    for idx, score, mtype, text in low_conf:
        print(f"  [{idx}] {score:.3f} ({mtype}): {text}...")

    # Page coverage
    pages = set()
    for p in paragraphs:
        for pg in range(p["start_page"], p["end_page"] + 1):
            pages.add(pg)
    print(f"\n📄 Page coverage: {min(pages)} to {max(pages)}")
    print(f"   Total unique pages: {len(pages)}")

    # Check page order (two types of violations)
    out_of_order = []
    prev_start = 0
    prev_end = 0
    for i, p in enumerate(paragraphs):
        # Type 1: start_page goes backwards
        if p["start_page"] < prev_start:
            out_of_order.append((i, "start<prev_start", prev_start, p["start_page"]))
        # Type 2: previous end_page > current start_page (overlap/out-of-order)
        if prev_end > p["start_page"]:
            out_of_order.append((i, "prev_end>start", prev_end, p["start_page"]))
        prev_start = p["start_page"]
        prev_end = p["end_page"]
    print(f"\n🔢 Page order violations: {len(out_of_order)}")
    for idx, vtype, prev, curr in out_of_order[:10]:
        print(f"  [{idx}] {vtype}: prev={prev}, curr={curr}")

    # Missing page ranges (gaps > 1)
    sorted_pages = sorted(pages)
    gaps = []
    for i in range(len(sorted_pages) - 1):
        gap = sorted_pages[i + 1] - sorted_pages[i]
        if gap > 1:
            gaps.append((sorted_pages[i], sorted_pages[i + 1], gap - 1))
    print(f"\n⚠️  Missing page gaps: {len(gaps)}")
    for start, end, count in gaps:
        print(f"  Pages {start + 1}-{end - 1} missing ({count} pages)")

    return {
        "total_paragraphs": len(paragraphs),
        "low_confidence": len(low_conf),
        "page_range": (min(pages), max(pages)),
        "unique_pages": len(pages),
        "order_violations": len(out_of_order),
        "gaps": gaps,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python -m examples.ocr_cleanup.tools.verify_merge <final_pages.json>"
        )
        sys.exit(1)
    verify_merge(sys.argv[1])
