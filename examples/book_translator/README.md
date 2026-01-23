# Book Translator Example

Translate books and documents using YAMLGraph with:
- **Two-phase splitting** - LLM identifies chapters, Python splits reliably
- **Parallel chunk translation** via map nodes
- **Glossary consistency** via term extraction
- **Quality gates** with optional human review
- **Resume support** via SQLite checkpointing

## Quick Start

```bash
# Translate the sample Finnish war diary → English
yamlgraph graph run examples/book_translator/graph.yaml \
  --var source_text="$(cat examples/book_translator/spk-kekkonen)" \
  --var source_language="Finnish" \
  --var target_language="English" \
  --var 'glossary={}' \
  --full
```

## Pipeline Flow

```
┌──────────────────┐    ┌────────────┐    ┌─────────────────┐
│identify_chapters │───▶│ split_book │───▶│ extract_glossary│
│     (LLM)        │    │  (Python)  │    │ (map - parallel)│
└──────────────────┘    └────────────┘    └────────┬────────┘
                                                   │
                                                   ▼
┌──────────────────┐    ┌─────────────────┐    ┌──────────────┐
│  translate_all   │◀───│ merge_glossary  │◀───│term_extractions
│ (map - parallel) │    │    (Python)     │    └──────────────┘
└────────┬─────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌──────────────┐    ┌────────────────┐
│  proofread_all  │───▶│quality_check │───▶│  human_review  │
│ (map - parallel)│    │   (Python)   │    │ (if needed)    │
└─────────────────┘    └──────┬───────┘    └───────┬────────┘
                              │                    │
                              ▼                    ▼
                       ┌──────────┐         ┌──────────┐
                       │reassemble│◀────────│reassemble│
                       │ (Python) │         └──────────┘
                       └──────────┘
```

## File Structure

```
examples/book_translator/
├── graph.yaml              # Main pipeline definition
├── prompts/
│   ├── identify_chapters.yaml  # LLM chapter marker identification
│   ├── extract_terms.yaml      # Glossary extraction per chunk
│   ├── translate_chunk.yaml    # Translation prompt
│   └── proofread.yaml          # Quality check prompt
├── nodes/
│   └── tools.py            # Python tools: split, merge, check, join
├── sample_book.txt         # Sample German text
├── spk-kekkonen            # Finnish Winter War diary (17KB)
└── README.md               # This file
```

## Key Design Decisions

### Two-Phase Splitting

1. **LLM identifies markers** - Finds semantic boundaries (chapter headings, dates)
2. **Python splits text** - Reliable string operations using those markers

This avoids LLM hallucination in actual text manipulation.

### Context Preservation

Each chunk includes overlapping context:
- `context_before`: Last 300 chars from previous chunk
- `context_after`: First 300 chars from next chunk

This helps the LLM maintain narrative coherence across chunk boundaries.

### Glossary Accumulation

Terms are extracted per-chunk in parallel, then merged. Existing terms are never overwritten, ensuring consistency.

## Usage Options

### With Initial Glossary

```bash
yamlgraph graph run examples/book_translator/graph.yaml \
  --var source_text="$(cat my_book.txt)" \
  --var source_language="German" \
  --var target_language="English" \
  --var 'glossary={"Rotkäppchen": "Little Red Riding Hood"}'
```

### View Full Output

```bash
yamlgraph graph run examples/book_translator/graph.yaml \
  --var source_text="$(cat my_book.txt)" \
  --var source_language="Finnish" \
  --var target_language="English" \
  --var 'glossary={}' \
  --full  # Show all state fields
```

### Resume Interrupted Translation

```bash
yamlgraph graph resume <thread-id>
```

## Python API

```python
from yamlgraph.graph_loader import load_and_compile
from pathlib import Path

# Load book
book_text = Path("examples/book_translator/spk-kekkonen").read_text()

# Compile and run
graph, checkpointer = load_and_compile("examples/book_translator/graph.yaml")
app = graph.compile(checkpointer=checkpointer)

result = app.invoke({
    "source_text": book_text,
    "source_language": "Finnish",
    "target_language": "English",
    "glossary": {},
})

print(result["final_text"])
```

## Customization

### Different Languages

The pipeline supports any language pair:
- `source_language`: The language of your input text
- `target_language`: The desired output language

### Provider Selection

Change the LLM provider in `graph.yaml` defaults:

```yaml
defaults:
  provider: openai  # or mistral, anthropic
  temperature: 0.3
```

### Quality Threshold

Chunks with `quality_score < 0.8` or `approved: false` are flagged for human review.

## Testing

```bash
# Run all book_translator tests
pytest tests/unit/test_book_translator_*.py -v --no-cov
```

## Node Reference

| Node | Type | Purpose |
|------|------|---------|
| `identify_chapters` | LLM | Find semantic chapter boundaries |
| `split_book` | Python | Split text at identified markers |
| `extract_glossary` | Map (LLM) | Extract terms per chunk in parallel |
| `merge_glossary` | Python | Combine extracted terms |
| `translate_all` | Map (LLM) | Translate chunks in parallel |
| `proofread_all` | Map (LLM) | Quality check translations |
| `quality_check` | Python | Flag low-quality chunks |
| `human_review` | Interrupt | Optional human correction |
| `reassemble` | Python | Join chunks into final text |
