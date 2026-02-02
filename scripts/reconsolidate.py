#!/usr/bin/env python3
"""Re-consolidate batch files with fixed merge logic."""

import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.ocr_cleanup.run import _write_plain_text, consolidate_batches


def reconsolidate(output_dir: Path) -> None:
    """Re-run consolidation on existing batch files."""
    batch_files = sorted(output_dir.glob("batch_*.json"))
    print(f"Found {len(batch_files)} batch files in {output_dir.name}")

    # Re-consolidate with fixed logic
    final = consolidate_batches(batch_files, output_dir)

    # Merge retry results if they exist
    retry_file = output_dir / "retried_pages.json"
    if retry_file.exists():
        retry_results = json.loads(retry_file.read_text())
        if retry_results.get("paragraphs"):
            print(f"Merging {len(retry_results['paragraphs'])} recovered paragraphs...")
            all_paras = final["paragraphs"] + retry_results["paragraphs"]
            all_paras.sort(key=lambda p: (p.get("start_page", 0), p.get("end_page", 0)))
            final["paragraphs"] = all_paras
            final["stats"]["total_paragraphs"] = len(all_paras)

            # Rewrite final files
            final_json = output_dir / "final.json"
            final_json.write_text(json.dumps(final, ensure_ascii=False, indent=2))
            _write_plain_text(final, output_dir / "final.txt")

    print(f"Done! {final['stats']['total_paragraphs']} paragraphs")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reconsolidate.py <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    if not output_dir.exists():
        print(f"Directory not found: {output_dir}")
        sys.exit(1)

    reconsolidate(output_dir)
