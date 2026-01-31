#!/usr/bin/env python3
"""OCR Cleanup Runner - Batch processing for full PDFs.

Usage:
    python -m examples.ocr_cleanup.run path/to/document.pdf --workers 10

Features:
- Batch execution with configurable page count per batch
- Resume support (skips completed batches)
- Automatic retry of failed pages
- Page-specific intermediate results
- Final consolidation with cross-batch paragraph merging
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def get_pdf_page_count(pdf_path: Path) -> int:
    """Get total page count from PDF using pdfinfo."""
    result = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    raise ValueError(f"Could not determine page count for {pdf_path}")


def find_failed_pages(batch_result: dict, start_page: int, end_page: int) -> list[int]:
    """Find pages that failed processing in a batch.

    Compares expected pages (start_page to end_page) against pages
    that appear in the paragraphs output.
    """
    processed_pages = set()
    for para in batch_result.get("paragraphs", []):
        if para.get("start_page"):
            processed_pages.add(para["start_page"])
        if para.get("end_page"):
            processed_pages.add(para["end_page"])

    expected_pages = set(range(start_page, end_page + 1))
    failed = sorted(expected_pages - processed_pages)
    return failed


def retry_failed_pages(
    pdf_path: Path,
    failed_pages: list[int],
    output_dir: Path,
    use_async: bool = True,
    max_retries: int = 3,
) -> dict:
    """Retry processing for individual failed pages.

    Returns dict with successful retries.
    """
    retry_results = {
        "paragraphs": [],
        "corrections": [],
        "chapters": [],
        "errors": [],
        "retried_pages": [],
        "still_failed": [],
    }

    if not failed_pages:
        return retry_results

    print(f"\n🔄 Retrying {len(failed_pages)} failed pages: {failed_pages}")

    for page_num in failed_pages:
        success = False

        for attempt in range(max_retries):
            print(f"  📄 Page {page_num} (attempt {attempt + 1}/{max_retries})...")

            try:
                import asyncio

                from yamlgraph.graph_loader import compile_graph, load_graph_config

                config = load_graph_config("examples/ocr_cleanup/graph.yaml")
                builder = compile_graph(config)
                graph = builder.compile()

                initial = {
                    "pdf_path": str(pdf_path),
                    "start_page": page_num,
                    "end_page": page_num,
                }

                if use_async:
                    state = asyncio.run(graph.ainvoke(initial))
                else:
                    state = graph.invoke(initial)

                paragraphs = state.get("paragraphs", [])

                if paragraphs:
                    retry_results["paragraphs"].extend(paragraphs)
                    retry_results["corrections"].extend(state.get("corrections", []))
                    retry_results["chapters"].extend(state.get("chapters", []))
                    retry_results["retried_pages"].append(page_num)
                    print(
                        f"  ✅ Page {page_num} recovered: {len(paragraphs)} paragraphs"
                    )
                    success = True
                    break

            except Exception as e:
                if attempt == max_retries - 1:
                    retry_results["errors"].append(f"Page {page_num}: {e}")

        if not success:
            retry_results["still_failed"].append(page_num)
            print(f"  ❌ Page {page_num} still failed after {max_retries} attempts")

    # Save retry results
    if retry_results["retried_pages"]:
        retry_file = output_dir / "retried_pages.json"
        retry_file.write_text(json.dumps(retry_results, ensure_ascii=False, indent=2))
        print(f"\n💾 Retry results saved: {retry_file}")

    return retry_results


def run_batch(
    pdf_path: Path,
    start_page: int,
    end_page: int,
    output_file: Path,
    use_async: bool = True,
) -> dict | None:
    """Run yamlgraph on a page range and save results."""
    if output_file.exists():
        print(f"  ⏭️  Batch {start_page}-{end_page} already complete, skipping")
        return json.loads(output_file.read_text())

    print(f"  🔄 Processing pages {start_page}-{end_page}...")

    try:
        import asyncio

        from yamlgraph.graph_loader import compile_graph, load_graph_config

        config = load_graph_config("examples/ocr_cleanup/graph.yaml")
        builder = compile_graph(config)
        graph = builder.compile()

        initial = {
            "pdf_path": str(pdf_path),
            "start_page": start_page,
            "end_page": end_page,
        }

        if use_async:
            state = asyncio.run(graph.ainvoke(initial))
        else:
            state = graph.invoke(initial)

        # Extract relevant fields
        batch_result = {
            "start_page": start_page,
            "end_page": end_page,
            "paragraphs": state.get("paragraphs", []),
            "corrections": state.get("corrections", []),
            "chapters": state.get("chapters", []),
            "stats": state.get("stats", {}),
            "errors": [str(e) for e in state.get("errors", [])],
            "failed_pages": find_failed_pages(
                {"paragraphs": state.get("paragraphs", [])},
                start_page,
                end_page,
            ),
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(batch_result, ensure_ascii=False, indent=2))
        print(
            f"  ✅ Batch {start_page}-{end_page} complete: {len(batch_result['paragraphs'])} paragraphs"
        )
        return batch_result

    except Exception as e:
        print(f"  ❌ Batch {start_page}-{end_page} error: {e}")
        import traceback

        traceback.print_exc()
        return None


def consolidate_batches(batch_files: list[Path], output_dir: Path) -> dict:
    """Merge all batch results into final output.

    Handles:
    - Paragraph merging across batch boundaries
    - Correction aggregation
    - Chapter list assembly
    - Statistics summation
    """
    all_paragraphs = []
    all_corrections = []
    all_chapters = []
    total_errors = []

    pending_paragraph = None  # For cross-batch continuation

    for batch_file in sorted(batch_files, key=lambda f: int(f.stem.split("_")[1])):
        batch = json.loads(batch_file.read_text())

        paragraphs = batch.get("paragraphs", [])

        for i, para in enumerate(paragraphs):
            text = para.get("text", "")
            start_page = para.get("start_page")
            end_page = para.get("end_page")

            # Check if this continues from previous batch
            if i == 0 and pending_paragraph:
                # Merge with pending
                text = pending_paragraph["text"] + " " + text
                start_page = pending_paragraph["start_page"]
                pending_paragraph = None

            # Check if this continues to next batch (last paragraph, ends mid-sentence)
            if i == len(paragraphs) - 1 and text.rstrip()[-1] not in ".!?\"'":
                pending_paragraph = {
                    "text": text,
                    "start_page": start_page,
                    "end_page": end_page,
                }
                continue

            all_paragraphs.append(
                {
                    "text": text,
                    "start_page": start_page,
                    "end_page": end_page,
                }
            )

        all_corrections.extend(batch.get("corrections", []))
        all_chapters.extend(batch.get("chapters", []))
        total_errors.extend(batch.get("errors", []))

    # Flush any remaining pending paragraph
    if pending_paragraph:
        all_paragraphs.append(pending_paragraph)

    # Build final result
    final = {
        "paragraphs": all_paragraphs,
        "corrections": all_corrections,
        "chapters": all_chapters,
        "stats": {
            "total_paragraphs": len(all_paragraphs),
            "total_corrections": len(all_corrections),
            "total_chapters": len(all_chapters),
            "total_errors": len(total_errors),
        },
        "errors": total_errors,
    }

    # Write final JSON
    final_json = output_dir / "final.json"
    final_json.write_text(json.dumps(final, ensure_ascii=False, indent=2))

    # Write plain text version
    final_txt = output_dir / "final.txt"
    _write_plain_text(final, final_txt)

    print(f"\n📄 Final output: {final_json}")
    print(f"📝 Plain text: {final_txt}")
    print(f"📊 Stats: {final['stats']}")

    return final


def _write_plain_text(final: dict, output_path: Path) -> None:
    """Write plain text version of the final output."""
    text_lines = []
    current_chapter = None
    all_paragraphs = final.get("paragraphs", [])
    all_chapters = final.get("chapters", [])

    for para in all_paragraphs:
        # Check for chapter
        for ch in all_chapters:
            if ch.get("start_page") == para.get(
                "start_page"
            ) and current_chapter != ch.get("title"):
                current_chapter = ch.get("title")
                text_lines.append(f"\n\n{'='*60}\n{current_chapter}\n{'='*60}\n\n")

        text_lines.append(para.get("text", ""))
        text_lines.append("\n\n")

    output_path.write_text("".join(text_lines))


def main():
    parser = argparse.ArgumentParser(description="OCR Cleanup - Full PDF processing")
    parser.add_argument("pdf_path", type=Path, help="Path to PDF file")
    parser.add_argument(
        "--workers", "-w", type=int, default=10, help="Pages per batch (default: 10)"
    )
    parser.add_argument(
        "--start", "-s", type=int, default=1, help="Start page (default: 1)"
    )
    parser.add_argument(
        "--end", "-e", type=int, default=None, help="End page (default: last page)"
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=None, help="Output directory"
    )
    parser.add_argument(
        "--sync", action="store_true", help="Use sync execution (slower)"
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path.resolve()
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        output_dir = Path("outputs/ocr_cleanup") / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get page count
    total_pages = get_pdf_page_count(pdf_path)
    start_page = args.start
    end_page = args.end or total_pages

    print(f"📚 Processing: {pdf_path.name}")
    print(f"   Pages: {start_page}-{end_page} of {total_pages}")
    print(f"   Batch size: {args.workers} pages")
    print(f"   Output: {output_dir}")
    print(f"   Mode: {'sync' if args.sync else 'async (parallel)'}")
    print()

    # Process in batches
    batch_files = []
    all_failed_pages = []
    current_page = start_page
    batch_num = 0

    while current_page <= end_page:
        batch_end = min(current_page + args.workers - 1, end_page)
        batch_file = output_dir / f"batch_{batch_num:03d}.json"

        result = run_batch(
            pdf_path=pdf_path,
            start_page=current_page,
            end_page=batch_end,
            output_file=batch_file,
            use_async=not args.sync,
        )

        if result:
            batch_files.append(batch_file)
            # Collect failed pages
            failed = result.get("failed_pages", [])
            if failed:
                all_failed_pages.extend(failed)
                print(f"    ⚠️  {len(failed)} pages need retry: {failed}")

        current_page = batch_end + 1
        batch_num += 1

    # Retry failed pages
    retry_results = None
    if all_failed_pages:
        retry_results = retry_failed_pages(
            pdf_path=pdf_path,
            failed_pages=all_failed_pages,
            output_dir=output_dir,
            use_async=not args.sync,
        )

    # Consolidate
    print(f"\n🔗 Consolidating {len(batch_files)} batches...")
    final = consolidate_batches(batch_files, output_dir)

    # Merge retry results into final
    if retry_results and retry_results.get("paragraphs"):
        print(f"📎 Merging {len(retry_results['paragraphs'])} recovered paragraphs...")

        # Insert recovered paragraphs in correct page order
        all_paras = final["paragraphs"] + retry_results["paragraphs"]
        all_paras.sort(key=lambda p: (p.get("start_page", 0), p.get("end_page", 0)))

        final["paragraphs"] = all_paras
        final["corrections"].extend(retry_results.get("corrections", []))
        final["chapters"].extend(retry_results.get("chapters", []))
        final["stats"]["total_paragraphs"] = len(all_paras)
        final["stats"]["total_corrections"] = len(final["corrections"])
        final["stats"]["retried_pages"] = len(retry_results.get("retried_pages", []))
        final["stats"]["still_failed_pages"] = retry_results.get("still_failed", [])

        # Rewrite final files
        final_json = output_dir / "final.json"
        final_json.write_text(json.dumps(final, ensure_ascii=False, indent=2))

        # Regenerate plain text
        _write_plain_text(final, output_dir / "final.txt")

        print(f"📊 Updated stats: {final['stats']}")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
