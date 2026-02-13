# Porting Plan: Kertomus Pipeline → YAMLGraph

## Background

The **kertomus-scripts** pipeline converts FHIR healthcare bundles into Finnish medical records ("Kertomus") through a 6-stage pipeline. Currently implemented as bash + Python scripts with Google Vertex AI (Gemini 2.5 Pro). A LangGraph port was attempted (`kertomus-langgraph/`) but abandoned — LangGraph added 690 lines of orchestration boilerplate (~5.5% of codebase) without delivering its value-adds (checkpointing, conditional routing, error recovery).

### Why YAMLGraph Instead

The LangGraph port failed because it was all scaffolding, no payoff. YAMLGraph inverts this — the 690 lines of boilerplate become ~80 lines of YAML, and the framework provides provider abstraction, prompt management, checkpointing, validation, and observability for free.

### Data Source

FHIR bundles sourced from Synthea: https://synthetichealth.github.io/synthea-sample-data/downloads/latest/synthea_sample_data_fhir_latest.zip

### Key Constraints

- **LLM provider**: Uses YAMLGraph's configured defaults — whatever provider is set via env vars (`PROVIDER`, `*_API_KEY`). Original pipeline used Gemini 2.5 Pro via Vertex AI; any YAMLGraph provider works. No provider or model hardcoded in graph metadata.
- **Concurrency**: 16 workers for kertomus/summary generation, 6 for patient history sections. Map nodes handle parallelism via LangGraph `Send()`.
- **State model: file-path-based.** Each stage writes output files to disk and passes file paths through state — not raw content. This keeps state small (~100 paths vs. megabytes of text) and preserves the existing file-based pipeline output structure. Tool nodes handle disk I/O; LLM nodes receive content loaded by preceding tool nodes.
- **No Pydantic schemas**: All LLM outputs are free-form text/markdown. Inline YAML schemas can enforce structure on validation outputs.
- **Finnish medical domain**: Prompts are substantial (130+ lines each). Already externalized in markdown — conversion to YAML prompt format is mechanical.

---

## Pipeline Mapping: kertomus-scripts → YAMLGraph

| Stage | kertomus-scripts | YAMLGraph Node Type | Notes |
|-------|-----------------|---------------------|-------|
| 1. FHIR Extraction | `fhir_components/*.py` (4 steps) | `type: python` tool node | Pure Python, no LLM. Wrap as tool. |
| 2. Kertomus Generation | `kertomus_generator.py` (16 workers) | `type: map` → `type: llm` | Map over encounter bundles, each calls LLM |
| 3. Visit Summarization | `visit_summarizer/` (16 workers) | `type: map` → `type: llm` | Map over kertomus files, each calls LLM |
| 4. Patient History | `patient_history/` (6 sections) | `type: map` → `type: llm` | Map over 6 section prompts, merge results |
| 5. Validation | `validator.py` + `history_validator.py` | `type: map` → `type: llm` | LLM-as-judge on pairs |
| 6. Link Enhancement | `history_linker.py` | `type: python` tool node | Pure regex, no LLM |

---

## Bare Bones Implementation Plan

### Phase 1: Foundation

#### `projects/synthetic-data/kertomus/graph.yaml` (NEW)
- Define 6-node linear pipeline: `extract_fhir → generate_kertomus → summarize → build_history → validate → enhance`
- Wire START → extract_fhir → ... → enhance → END
- Config section: `max_tokens: 8192` (provider/model from environment defaults)
- Variables: `bundle_path` (input FHIR JSON path), `output_dir`, `workers`

#### `projects/synthetic-data/kertomus/prompts/conversion.yaml` (NEW)
- Convert `kertomus-scripts/prompts/conversion-prompt.md` + `kertomus-structure.md` to YAML prompt format
- System prompt: Finnish medical documentation specialist role
- User prompt: Jinja2 template with `{{ fhir_data }}` variable
- No schema (free-form markdown output)

#### `projects/synthetic-data/kertomus/prompts/oneliner.yaml` (NEW)
- Convert `kertomus-scripts/prompts/oneliner-prompt.txt` to YAML prompt format
- User prompt: `{{ kertomus_text }}` variable
- No schema (free-form one-line output)

#### `projects/synthetic-data/kertomus/prompts/section_*.yaml` (NEW — 6 files, flat in prompts/)
- `section_executive_summary.yaml`, `section_timeline_events.yaml`, `section_procedures.yaml`, `section_treatment_phases.yaml`, `section_medications.yaml`, `section_conclusions.yaml`
- Each gets `{{ patient_data }}` + `{{ visits }}` variables
- Note: Dynamic prompt paths (`prompts/sections/{item}`) are NOT a YAMLGraph feature. Each section is a separate explicit node in the graph.

#### `projects/synthetic-data/kertomus/prompts/validation_history.yaml` (NEW)
- Convert `kertomus-scripts/prompts/history_validation.md`
- Variables: `{{ summaries_content }}`, `{{ history_content }}`
- Inline schema: same rating structure

### Phase 2: Tool Nodes

#### `projects/synthetic-data/kertomus/nodes/fhir_extractor.py` (NEW)
- Wrap `fhir_components/` pipeline: extract → associate → reconstruct → validate
- Input: `state["bundle_path"]` (FHIR JSON path), `state["output_dir"]`
- Output: `{ fhir_result: { bundle_paths: list[str], patient_info: str, fhir_dir: str } }`
- Note: Returns file **paths** to reconstructed bundles, not full JSON content
- Copy/adapt the 4 fhir_components Python files into this module
- No LLM dependency — pure FHIR JSON parsing
- Must be declared in `tools:` section as `type: python`

#### `projects/synthetic-data/kertomus/nodes/bundle_loader.py` (NEW)
- Reads a single encounter bundle JSON from disk path, returns content for LLM prompt
- Input: `state["bundle_path"]` (single file path from map iteration)
- Output: `{ fhir_data: str }` (JSON content, truncated to 8000 chars as in original)
- Must be declared in `tools:` section as `type: python`

#### `projects/synthetic-data/kertomus/nodes/file_writer.py` (NEW)
- Utility tool for writing LLM outputs to files (kertomus/*.md, summaries/*.txt, histories/*.md)
- Input: content + output_path from state
- Output: `{ written_path: str }`
- Must be declared in `tools:` section as `type: python`

#### `projects/synthetic-data/kertomus/nodes/history_merger.py` (NEW)
- Adapt `patient_history/merger.py` — combine 6 section outputs into single document
- Input: `state["history_sections"]` (list of section dicts from map collect)
- Output: `{ patient_history: str, history_path: str }`
- Validate: must contain required Finnish section headers, ≥500 chars
- Writes merged history to disk, returns path
- Must be declared in `tools:` section as `type: python`

#### `projects/synthetic-data/kertomus/nodes/link_enhancer.py` (NEW)
- Adapt `history_linker.py` — regex-based date→link conversion
- Input: `state["history_path"]` + `state["fhir_result"]["fhir_dir"]` (for file mapping)
- Output: `{ enhanced_history: str, enhanced_path: str }`
- 6 regex patterns for reference replacement
- Reads from disk, writes enhanced version, returns path
- Must be declared in `tools:` section as `type: python`

### Phase 3: Graph Wiring

#### `projects/synthetic-data/kertomus/graph.yaml` (CHANGE — flesh out nodes)

```yaml
version: "1.0"
name: kertomus-pipeline
description: "FHIR → Finnish Medical Records pipeline"

metadata:
  temperature: 0.1

config:
  max_map_items: 50
  timeout: 600

# Python tools must be declared in tools section
tools:
  fhir_extractor:
    type: python
    module: nodes.fhir_extractor
    function: extract
    description: "Extract FHIR bundles into encounter files"

  bundle_loader:
    type: python
    module: nodes.bundle_loader
    function: load_bundle
    description: "Load a single encounter bundle from disk path"

  file_writer:
    type: python
    module: nodes.file_writer
    function: write_output
    description: "Write content to file on disk"

  history_merger:
    type: python
    module: nodes.history_merger
    function: merge
    description: "Merge 6 history sections into single document"

  link_enhancer:
    type: python
    module: nodes.link_enhancer
    function: enhance
    description: "Convert date references to clickable links"

nodes:
  # Stage 1: FHIR extraction (no LLM)
  extract_fhir:
    type: python
    tool: fhir_extractor
    state_key: fhir_result

  # Stage 2: Generate Finnish medical records (map over encounter bundle paths)
  generate_kertomus:
    type: map
    over: "{state.fhir_result.bundle_paths}"
    as: bundle_path
    max_items: 50
    node:
      type: llm
      prompt: prompts/conversion
      variables:
        fhir_data: "{state.bundle_path}"
      state_key: kertomus_text
    collect: kertomus_records

  # Stage 3: Summarize each kertomus to one-liner
  summarize:
    type: map
    over: "{state.kertomus_records}"
    as: kertomus_item
    max_items: 50
    node:
      type: llm
      prompt: prompts/oneliner
      variables:
        kertomus_text: "{state.kertomus_item}"
      state_key: summary_text
    collect: summaries

  # Stage 4: Build patient history — 6 explicit section nodes
  # (Dynamic prompt paths are not supported, so each section is explicit)
  section_executive_summary:
    type: llm
    prompt: prompts/section_executive_summary
    variables:
      patient_data: "{state.fhir_result.patient_info}"
      visits: "{state.summaries}"
    state_key: sec_executive_summary
    requires: [summaries]

  section_timeline_events:
    type: llm
    prompt: prompts/section_timeline_events
    variables:
      patient_data: "{state.fhir_result.patient_info}"
      visits: "{state.summaries}"
    state_key: sec_timeline_events
    requires: [summaries]

  section_procedures:
    type: llm
    prompt: prompts/section_procedures
    variables:
      patient_data: "{state.fhir_result.patient_info}"
      visits: "{state.summaries}"
    state_key: sec_procedures
    requires: [summaries]

  section_treatment_phases:
    type: llm
    prompt: prompts/section_treatment_phases
    variables:
      patient_data: "{state.fhir_result.patient_info}"
      visits: "{state.summaries}"
    state_key: sec_treatment_phases
    requires: [summaries]

  section_medications:
    type: llm
    prompt: prompts/section_medications
    variables:
      patient_data: "{state.fhir_result.patient_info}"
      visits: "{state.summaries}"
    state_key: sec_medications
    requires: [summaries]

  section_conclusions:
    type: llm
    prompt: prompts/section_conclusions
    variables:
      patient_data: "{state.fhir_result.patient_info}"
      visits: "{state.summaries}"
    state_key: sec_conclusions
    requires: [summaries]

  # Stage 4b: Merge sections
  merge_history:
    type: python
    tool: history_merger
    requires: [sec_executive_summary, sec_timeline_events, sec_procedures,
               sec_treatment_phases, sec_medications, sec_conclusions]
    state_key: patient_history

  # Stage 5: Validate history against summaries
  validate:
    type: llm
    prompt: prompts/validation_history
    variables:
      summaries_content: "{state.summaries}"
      history_content: "{state.patient_history}"
    state_key: validation_result
    requires: [patient_history]

  # Stage 6: Enhance with clickable date links
  enhance:
    type: python
    tool: link_enhancer
    requires: [patient_history, fhir_result]
    state_key: enhanced_history

edges:
  - from: START
    to: extract_fhir
  - from: extract_fhir
    to: generate_kertomus
  - from: generate_kertomus
    to: summarize
  # Fan-out: all 6 sections run from summarize (parallel via LangGraph)
  - from: summarize
    to: section_executive_summary
  - from: summarize
    to: section_timeline_events
  - from: summarize
    to: section_procedures
  - from: summarize
    to: section_treatment_phases
  - from: summarize
    to: section_medications
  - from: summarize
    to: section_conclusions
  # Fan-in: all sections merge
  - from: section_executive_summary
    to: merge_history
  - from: section_timeline_events
    to: merge_history
  - from: section_procedures
    to: merge_history
  - from: section_treatment_phases
    to: merge_history
  - from: section_medications
    to: merge_history
  - from: section_conclusions
    to: merge_history
  - from: merge_history
    to: validate
  - from: validate
    to: enhance
  - from: enhance
    to: END
```

**Architecture note:** The 6 section nodes fan out from `summarize` and fan in to `merge_history`. LangGraph executes nodes with satisfied dependencies in parallel, so the 6 sections run concurrently — achieving the same 6-worker parallelism as the original `concurrent_generator.py` without explicit threading.

### Phase 4: Demo Script

#### `projects/synthetic-data/kertomus/demo.py` (NEW)
- CLI entry point: `python demo.py source/patient_bundle.json --output results/`
- Loads graph, compiles, invokes with `{ bundle_path: path, output_dir: dir }`
- Writes final outputs to disk (kertomus/, summaries/, histories/)
- Progress reporting per stage

### Phase 5: Testing

#### `projects/synthetic-data/kertomus/tests/test_graph_lint.py` (NEW)
- Lint the graph.yaml — no errors expected
- Validate all prompt YAML files load correctly

#### `projects/synthetic-data/kertomus/tests/test_fhir_extractor.py` (NEW)
- Unit test with a small synthetic FHIR bundle
- Validate encounter extraction, association, reconstruction

#### `projects/synthetic-data/kertomus/tests/test_prompts.py` (NEW)
- Verify all prompts render without errors with sample variables
- Check Jinja2 templates compile

---

## What Gets Eliminated

| kertomus-scripts | Replaced By | Lines Saved |
|-----------------|-------------|-------------|
| `kertomus_pipeline.sh` (534 lines) | `graph.yaml` (~60 lines) | ~474 |
| `kertomus_folder.sh` (72 lines) | CLI `--var bundle_path=...` loop | ~72 |
| `kertomus_generator.py` (214 lines) | `generate_kertomus` map node | ~214 |
| `utils/llm_client.py` (361 lines) | YAMLGraph `create_llm()` factory | ~361 |
| `patient_history.py` (153 lines) | `build_history` map node | ~153 |
| `patient_history/concurrent_generator.py` (185 lines) | `build_history` map node | ~185 |
| `patient_history/section_processor.py` (149 lines) | Section prompt YAML files | ~149 |
| `patient_history/merger.py` (115 lines) | `nodes/history_merger.py` (~60 lines) | ~55 |
| `visit_summarizer/summarizer.py` (630 lines) | `summarize` map node | ~630 |
| `visit_summarizer/pipeline.py` (567 lines) | Graph orchestration | ~567 |
| All bash orchestration, worker pool mgmt | YAMLGraph map nodes | ~500 |
| **Total** | | **~3,360 lines** |

## What Gets Kept (adapted)

| Component | Lines | Reason |
|-----------|-------|--------|
| `fhir_components/*.py` | ~2,200 | Domain logic, no LLM — wrap as tool |
| `history_linker.py` | ~330 | Regex logic — wrap as tool |
| `visit_summarizer/timeline.py` | ~310 | Date parsing — wrap as tool |
| `visit_summarizer/quality.py` | ~500 | Quality gates — optional enhancement |
| Prompts (converted to YAML) | ~800 | Content preserved, format changed |

## What YAMLGraph Provides for Free

1. **Provider abstraction** — switch between Anthropic/OpenAI/Google/etc. with one env var
2. **Checkpointing** — resume interrupted pipeline from any stage (SQLite/Redis)
3. **LangSmith tracing** — observability on every LLM call, trace URLs
4. **Map nodes** — parallel fan-out without `ThreadPoolExecutor` boilerplate
5. **Error handling** — `on_error: retry` with configurable max_retries
6. **Validation** — graph linting catches structural issues before runtime
7. **CLI** — `yamlgraph graph run graph.yaml --var bundle_path=...`

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Map nodes may not support 16+ concurrent LLM calls efficiently | Start with default concurrency, profile, add `max_items` limits |
| FHIR data too large for state (encounter bundles) | Keep file paths in state, not full JSON; tool nodes read from disk |
| ~~Provider-specific safety settings~~ | ~~`create_llm()` doesn't pass `safety_settings`; only affects Google provider with medical content. Not a blocker.~~ |
| ~~Section-specific prompts need dynamic prompt path resolution~~ | ~~Resolved: 6 explicit section nodes (blocker #4)~~ |
| Pipeline needs file output at each stage (not just final state) | Tool nodes handle disk writes; state carries paths |

## Execution Order

1. Convert prompts to YAML format (mechanical, low risk)
2. Write `fhir_extractor.py` tool node (wrap existing code)
3. Write `graph.yaml` with first 2 nodes (extract + generate)
4. Test end-to-end with single encounter
5. Add remaining nodes incrementally
6. Add batch processing (kertomus_folder equivalent)
7. Add validation and quality gates

---

## Judgement

### Blockers — RESOLVED

1. **~~Map node syntax is wrong.~~** Fixed: map nodes now use `as` + `collect` (not `state_key`).

2. **~~Python node syntax is wrong.~~** Fixed: all Python tools declared in `tools:` section with `type: python`, `module`, `function`. Nodes reference via `tool:` property.

3. **~~Provider coupling.~~** Resolved: **use YAMLGraph configured defaults.** No provider or model hardcoded in graph metadata. Set `PROVIDER` and the corresponding `*_API_KEY` env var. Any YAMLGraph-supported provider works (anthropic, google, openai, mistral, xai, etc.).

4. **~~Dynamic prompt paths don't exist.~~** Fixed: 6 explicit section nodes (`section_executive_summary` through `section_conclusions`) fan out from `summarize` and fan in to `merge_history`. LangGraph runs them in parallel — same 6-worker concurrency as original.

5. **~~FHIR data too large for state.~~** Fixed: file-path-based model. FHIR extraction writes bundles to disk, passes `bundle_paths: list[str]` through state. Map nodes iterate over paths. LLM prompts receive content loaded at execution time, not stored in state.

6. **~~No file output between stages.~~** Fixed: tool nodes handle all disk I/O. State carries paths (`fhir_dir`, `bundle_paths`, `history_path`, `enhanced_path`). Tool node `file_writer` writes LLM outputs to disk after each map stage.

### Remaining Concerns (non-blocking)

- **Batch mode (100+ patients)**: Single-patient graph. Batch = CLI loop calling `yamlgraph graph run` per patient. Acceptable for Phase 1; kertomus_folder.sh equivalent is a thin wrapper.
- **LLM cost**: ~40-60 LLM calls per patient × ~8K output tokens. Cost varies by provider. Budget accordingly for 100 patient test runs.
- **`bundle_path` in map → LLM**: Map iterates over file paths, but LLM nodes need content. Python sub-nodes in maps ARE supported (FR-021 implemented, verified with `python-map` demo). Wire `bundle_loader` as a python sub-node before each LLM map to load file content — **resolve during Phase 3 wiring.**
- **`file_writer` unused in graph**: Declared but not wired. Add write nodes after map stages during Phase 3.
- **Safety settings**: `create_llm()` does not pass `safety_settings` to Google provider. Only relevant if using Google with medical content that triggers filters. Not a blocker — other providers unaffected.

### Verdict

**Authority granted for Phase 1 (prompts) and Phase 2 (tool nodes).** Phase 3 graph wiring should be tested incrementally — 2-node graph first, then expand.

---

## Deliverables by Phase

### Phase 1: Foundation — Prompts & Graph Skeleton

| # | Deliverable | Type | Description |
|---|------------|------|-------------|
| 1.1 | `projects/synthetic-data/kertomus/graph.yaml` | Graph | Skeleton with node declarations, edges, metadata |
| 1.2 | `projects/synthetic-data/kertomus/prompts/conversion.yaml` | Prompt | FHIR→Kertomus conversion (system + user, ~130 lines content) |
| 1.3 | `projects/synthetic-data/kertomus/prompts/oneliner.yaml` | Prompt | Kertomus→one-line summary (~35 lines content) |
| 1.4 | `projects/synthetic-data/kertomus/prompts/section_executive_summary.yaml` | Prompt | Executive summary section prompt |
| 1.5 | `projects/synthetic-data/kertomus/prompts/section_timeline_events.yaml` | Prompt | Timeline events section prompt |
| 1.6 | `projects/synthetic-data/kertomus/prompts/section_procedures.yaml` | Prompt | Procedures section prompt |
| 1.7 | `projects/synthetic-data/kertomus/prompts/section_treatment_phases.yaml` | Prompt | Treatment phases section prompt |
| 1.8 | `projects/synthetic-data/kertomus/prompts/section_medications.yaml` | Prompt | Medications section prompt |
| 1.9 | `projects/synthetic-data/kertomus/prompts/section_conclusions.yaml` | Prompt | Conclusions section prompt |
| 1.10 | `projects/synthetic-data/kertomus/prompts/validation_history.yaml` | Prompt | History validation (LLM-as-judge) with inline schema |

**Phase 1 outputs:** `yamlgraph graph lint projects/synthetic-data/kertomus/graph.yaml` passes. All prompts load without errors.

> Removed: `patient_history.yaml` (superseded by 6 section prompts) and `validation_summary.yaml` (no consuming node).

### Phase 2: Tool Nodes

| # | Deliverable | Type | Description |
|---|------------|------|-------------|
| 2.1 | `projects/synthetic-data/kertomus/nodes/__init__.py` | Code | Package init |
| 2.2 | `projects/synthetic-data/kertomus/nodes/fhir_extractor.py` | Code | Wraps fhir_components/ — extract→associate→reconstruct→validate |
| 2.3 | `projects/synthetic-data/kertomus/nodes/file_writer.py` | Code | Write LLM output to disk (kertomus/*.md, summaries/*.txt) |
| 2.4 | `projects/synthetic-data/kertomus/nodes/history_merger.py` | Code | Merge 6 sections into single patient history document |
| 2.5 | `projects/synthetic-data/kertomus/nodes/link_enhancer.py` | Code | Regex date→link conversion (6 patterns) |
| 2.6 | `projects/synthetic-data/kertomus/fhir_components/` | Code | Copied/adapted from kertomus-scripts (4 modules, ~2,200 lines) |

**Phase 2 outputs:** Each tool runs standalone with test inputs. `python -c "from nodes.fhir_extractor import extract"` works.

### Phase 3: Graph Wiring — Incremental

| # | Deliverable | Type | Description |
|---|------------|------|-------------|
| 3.1 | `graph.yaml` v1: extract + generate | Graph | 2-node graph: FHIR extraction → single kertomus generation |
| 3.2 | `graph.yaml` v2: + summarize | Graph | Add map-based summarization over kertomus outputs |
| 3.3 | `graph.yaml` v3: + history | Graph | Add 6-section parallel history generation + merge |
| 3.4 | `graph.yaml` v4: + validate + enhance | Graph | Full pipeline with validation and link enhancement |

**Phase 3 outputs per increment:**
- v1: `yamlgraph graph run graph.yaml --var bundle_path=source/patient.json` → produces kertomus markdown for each encounter
- v2: → also produces one-line summaries
- v3: → also produces merged patient history
- v4: → also produces validation report + enhanced history with links

### Phase 4: Demo & CLI

| # | Deliverable | Type | Description |
|---|------------|------|-------------|
| 4.1 | `projects/synthetic-data/kertomus/demo.py` | Code | CLI entry point with progress reporting, file output |
| 4.2 | `projects/synthetic-data/kertomus/demo.sh` | Script | Shell wrapper for demo.sh integration |
| 4.3 | `projects/synthetic-data/kertomus/README.md` | Docs | Setup, usage, sample output |

**Phase 4 outputs:**
- `python demo.py source/patient_bundle.json --output results/` → full pipeline run
- `results/kertomus/kertomus_encounter_*.md` — Finnish medical records (one per encounter)
- `results/summaries/summary_*.txt` — one-line visit summaries
- `results/histories/patient_history.md` — merged patient history
- `results/histories/patient_history_enhanced.md` — with clickable date links
- `results/validation-report.txt` — quality ratings

### Phase 5: Testing

| # | Deliverable | Type | Description |
|---|------------|------|-------------|
| 5.1 | `projects/synthetic-data/kertomus/tests/test_graph_lint.py` | Test | Graph lints without errors |
| 5.2 | `projects/synthetic-data/kertomus/tests/test_prompts.py` | Test | All prompts render with sample variables |
| 5.3 | `projects/synthetic-data/kertomus/tests/test_fhir_extractor.py` | Test | FHIR extraction with mini synthetic bundle |
| 5.4 | `projects/synthetic-data/kertomus/tests/test_history_merger.py` | Test | Section merge ordering + validation |
| 5.5 | `projects/synthetic-data/kertomus/tests/test_link_enhancer.py` | Test | Regex patterns match expected references |
| 5.6 | `projects/synthetic-data/kertomus/tests/fixtures/mini_bundle.json` | Fixture | Small synthetic FHIR bundle (2-3 encounters) |

**Phase 5 outputs:** `pytest projects/synthetic-data/kertomus/tests/ -v` — all green.

### Summary: Total Deliverables

| Phase | Files | Type Breakdown |
|-------|-------|---------------|
| 1. Foundation | 10 | 1 graph + 9 prompts |
| 2. Tool Nodes | 6+ | 5 Python modules + fhir_components/ |
| 3. Graph Wiring | 1 | graph.yaml iterated 4 times |
| 4. Demo & CLI | 3 | demo.py + demo.sh + README |
| 5. Testing | 6 | 5 test files + 1 fixture |
| **Total** | **~26** | **New files to create** |

### Expected Pipeline Outputs (per patient)

| Output | Format | Example Size |
|--------|--------|-------------|
| `fhir_organized/{patient_id}/` | Directory tree | ~50 files (encounters, observations, bundles) |
| `kertomus/kertomus_encounter_*.md` | Markdown | ~2KB each, 10-30 per patient |
| `summaries/summary_*.txt` | Text | ~200 bytes each, 10-30 per patient |
| `histories/patient_history.md` | Markdown | ~5-10KB (6 sections merged) |
| `histories/patient_history_enhanced.md` | Markdown | ~6-12KB (with date links) |
| `validation-report.txt` | Text | ~1KB (ratings + issues) |
| LangSmith traces | Remote | One trace per LLM call (~40-60 calls per patient)
