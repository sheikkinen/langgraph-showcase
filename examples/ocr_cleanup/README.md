# OCR Cleanup Pipeline

An example YAMLGraph pipeline that cleans up OCR text from scanned PDF documents using LLM-based processing.

## Overview

This pipeline:
1. **Extracts text** from PDF pages using `pdftotext` (preserving layout)
2. **Cleans each page** in parallel using an LLM to fix OCR artifacts
3. **Merges paragraphs** that span page boundaries
4. **Aggregates corrections** and generates statistics

## Prerequisites

- `pdftotext` (poppler-utils): `brew install poppler` (macOS) or `apt install poppler-utils` (Linux)
- YAMLGraph with LLM provider configured (default: Mistral)

## Usage

```bash
# Process full PDF
yamlgraph graph run examples/ocr_cleanup/graph.yaml \
  -v 'pdf_path=path/to/document.pdf'

# Process specific page range
yamlgraph graph run examples/ocr_cleanup/graph.yaml \
  -v 'pdf_path=path/to/document.pdf' \
  -v 'start_page=1' \
  -v 'end_page=10'
```

## Output

The pipeline produces structured output with:

- **paragraphs**: List of cleaned paragraphs with page references
- **corrections**: All OCR fixes applied (original → corrected)
- **chapters**: Detected chapter boundaries
- **stats**: Processing statistics

Example corrections:
```
ur- hoolliset → urhoolliset  (hyphenated word join)
varas- tosta → varastosta    (line-break hyphenation)
tahi → tai                   (archaic spelling normalized)
```

## Pipeline Structure

```
PDF → extract_text → cleanup_pages (map) → merge_paragraphs → Result
                          ↓
                    [parallel LLM calls]
```

### Nodes

| Node | Type | Description |
|------|------|-------------|
| `extract_text` | python | Extracts text from PDF pages |
| `cleanup_pages` | map | Parallel LLM cleanup of each page |
| `merge_paragraphs` | python | Joins paragraphs and aggregates results |

## Files

```
examples/ocr_cleanup/
├── graph.yaml                 # Pipeline definition
├── prompts/
│   └── cleanup_page.yaml      # LLM prompt for page cleanup
├── tools/
│   ├── pdf_extract.py         # PDF text extraction
│   └── merger.py              # Paragraph merging
└── tests/
    ├── test_pdf_extract.py
    ├── test_cleanup_prompt.py
    └── test_merger.py
```

## OCR Fixes Applied

The LLM identifies and fixes common OCR artifacts:

- **Hyphenated line breaks**: `ur-` + `hoolliset` → `urhoolliset`
- **Character misreads**: `■asunsa` → `asunsa`
- **Spacing issues**: `.    ..` → `...`
- **Paragraph boundaries**: Detects text continuing to next page

## Running Tests

```bash
python -m pytest examples/ocr_cleanup/tests/ -v
```

## Customization

### Different LLM Provider

Set `LLM_PROVIDER` environment variable or modify `graph.yaml`:

```yaml
metadata:
  llm:
    provider: anthropic
    model: claude-3-haiku-20240307
```

### Language

Edit `prompts/cleanup_page.yaml` to adjust for different languages (default: Finnish).

## Batch Processing (Full Books)

For processing entire books or large PDFs, use the batch runner which processes pages in configurable batches with resume support:

```bash
# Process full PDF (default: 10 pages per batch)
python -m examples.ocr_cleanup.run path/to/book.pdf

# Custom batch size
python -m examples.ocr_cleanup.run path/to/book.pdf --workers 20

# Process specific page range
python -m examples.ocr_cleanup.run path/to/book.pdf --start 50 --end 100

# Use synchronous mode (for providers that don't support async parallel)
python -m examples.ocr_cleanup.run path/to/book.pdf --sync
```

### Batch Runner Features

- **Resume support**: Automatically skips completed batches
- **Page-specific outputs**: Each batch saves to `batch_NNN.json`
- **Cross-batch merging**: Paragraphs spanning batch boundaries are joined
- **Final consolidation**: Produces `final.json` and `final.txt`

### Output Location

```
outputs/ocr_cleanup/{pdf_name}/
├── batch_000.json    # First batch results
├── batch_001.json    # Second batch results
├── ...
├── final.json        # Consolidated structured data
└── final.txt         # Clean text for reading
```

### Performance Tips

- Use `--workers 10-20` for Anthropic (true parallel execution)
- Use smaller batches (`--workers 5`) for Mistral/xAI (sequential execution)
- The `--async` flag (default) enables parallel LLM calls within batches
