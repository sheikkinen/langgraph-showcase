# Example Request: SOUP Inventory & Risk Narrative Generator

**Priority:** LOW  
**Type:** Example  
**Status:** Proposed  
**Effort:** 4–6 days  
**Requested:** 2026-01-30

## Summary

Create an example pipeline (`examples/soup/`) that generates a SOUP (Software of Unknown Provenance) inventory from a Python project, enriches each component with license and vulnerability metadata, computes risk classification, and produces exportable narratives (Markdown/JSON) suitable for regulated-software documentation.

**PoC target**: Run SOUP analysis against the YAMLGraph repository itself.

## Problem

Regulated software teams need to:

- Identify third-party dependencies (SOUP components)
- Document provenance (name/version/source/license)
- Assess security and maintenance risk
- Generate consistent risk narratives

This is typically manual, inconsistent, and time-consuming. A YAMLGraph example pipeline would demonstrate map nodes, tool nodes, and LLM narrative generation.

## Proposed Solution

An example graph in `examples/soup/` with:

### Pipeline Nodes

| Node | Type | Description |
|------|------|-------------|
| `discover_project` | python | Parse pyproject.toml, requirements.txt |
| `extract_dependencies` | python | Normalize to `{name, version, ecosystem}` |
| `enrich_components` | map | Parallel fetch license + vulnerability info |
| `score_risks` | python | Compute risk score per component |
| `generate_narratives` | llm | Risk narrative per component |
| `render_markdown` | python | Format as report |
| `write_outputs` | python | Save JSON + Markdown |

### Outputs

- `soup_inventory.json` - Structured component data
- `soup_report.md` - Human-readable report
- `soup_report.json` - LLM-generated narratives

### Example Usage

```bash
# Run SOUP analysis on YAMLGraph
python -m examples.soup.run . --out outputs/soup/yamlgraph

# Or via yamlgraph CLI
yamlgraph graph run examples/soup/graph.yaml \
  -v target_path=. \
  -v risk_profile=regulated \
  --full
```

### Example Graph (Sketch)

```yaml
version: "1.0"
name: soup_analyzer

state:
  target_path: str
  ecosystem: str
  risk_profile: str
  components: list
  enriched: list
  scored: list
  report_md: str

nodes:
  discover_project:
    type: python
    tool: discover_project

  extract_dependencies:
    type: python
    tool: extract_dependencies

  enrich_components:
    type: map
    items: "{{ components }}"
    node:
      id: enrich_one
      type: python
      tool: enrich_component

  score_risks:
    type: python
    tool: score_components

  generate_narratives:
    type: llm
    prompt: prompts/narratives

  render_markdown:
    type: python
    tool: render_markdown

  write_outputs:
    type: python
    tool: write_outputs

edges:
  - from: START
    to: discover_project
  - from: discover_project
    to: extract_dependencies
  - from: extract_dependencies
    to: enrich_components
  - from: enrich_components
    to: score_risks
  - from: score_risks
    to: generate_narratives
  - from: generate_narratives
    to: render_markdown
  - from: render_markdown
    to: write_outputs
  - from: write_outputs
    to: END
```

## Risk Model (Heuristics)

| Risk Type | Indicators |
|-----------|------------|
| **Security** | Critical/High CVEs, vulnerable version ranges |
| **Maintenance** | No release in N months, low activity |
| **License** | Copyleft vs permissive (policy-based) |
| **Criticality** | Runtime vs dev/test dependency |

## Scope Notes

- This is an **example pipeline**, not a core CLI command
- Outputs are documentation assistance, not compliance certification
- Reports include "human review required" header

## Acceptance Criteria

- [ ] Example pipeline in `examples/soup/`
- [ ] Supports Python dependency extraction from pyproject.toml and requirements.txt
- [ ] Produces normalized SOUP component list
- [ ] Enrichment populates license and vulnerability info
- [ ] Risk scoring produces explainable score + flags
- [ ] Markdown report with narrative per component
- [ ] PoC runs against YAMLGraph and outputs report
- [ ] Tests for extract/enrich/score functions
- [ ] README with usage instructions

## Alternatives Considered

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| External SBOM tools only | Misses narrative generation |
| Static spreadsheet template | No automation |
| Vulnerability scan only | Misses license/maintenance docs |

## Related

- [examples/codegen/](../examples/codegen/) - Tool-heavy pipeline
- [examples/yamlgraph_gen/](../examples/yamlgraph_gen/) - Meta-generation + validation
- [examples/book_translator/](../examples/book_translator/) - Map nodes for parallel work
