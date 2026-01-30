# Example Request: SOUP Doc Compiler (Hybrid SBOM + Narratives)

**Priority:** LOW  
**Type:** Example  
**Status:** Proposed  
**Effort:** 2–3 days  
**Requested:** 2026-01-30

## Summary

Create an example pipeline (`examples/soup/`) that uses **real SBOM tools** (Trivy/Syft) for dependency extraction, then adds YAMLGraph's value: policy scoring, contextual classification, LLM narratives, and doc-ready exports.

**Key insight**: SBOM tools are best at accurate inventory + standards output. YAMLGraph is best at policy, context, narratives, and repeatable doc packs. The strongest solution is hybrid.

**PoC target**: Run against the YAMLGraph repository itself.

## Architecture: Hybrid Approach

### Layer 1: SBOM Tools (External)

| Tool | Purpose |
|------|---------|
| **Trivy** | SBOM generation (`--format cyclonedx`) + vulnerability scan |
| **Syft** | Alternative SBOM generation (filesystem/container) |
| **OSV-Scanner** | Dependency-to-vuln matching |
| **cdxgen** | CycloneDX-first, multi-ecosystem SBOMs |

### Layer 2: YAMLGraph (This Pipeline)

| Capability | Description |
|------------|-------------|
| **Normalize + dedupe** | Parse SBOM into internal component list |
| **Policy scoring** | License rules, severity thresholds, maintenance windows |
| **Contextual classification** | Runtime vs dev, safety-relevant tags |
| **LLM narratives** | Generate doc-ready risk narratives per component |
| **Human review** | Interrupt nodes for audit checkpoints |
| **Export doc pack** | MD/JSON/CSV with repeatable runs |

## Proposed Solution

### Pipeline Nodes (Simplified)

| Node | Type | Description |
|------|------|-------------|
| `generate_sbom` | python | Shell out to `trivy fs --format cyclonedx` |
| `parse_sbom` | python | Parse CycloneDX JSON → normalized components |
| `score_risks` | python | Apply policy rules, classify criticality |
| `generate_narratives` | llm | Risk narrative per component |
| `write_outputs` | python | Save inventory + report |

### Outputs

- `sbom.json` - Standard CycloneDX SBOM (from Trivy)
- `soup_inventory.json` - Enriched + scored component data
- `soup_report.md` - Human-readable SOUP narratives

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
name: soup_compiler

state:
  target_path: str
  risk_profile: str
  sbom_path: str
  components: list
  scored: list
  report_md: str

tools:
  generate_sbom:
    type: python
    module: examples.soup.nodes
    function: generate_sbom
    description: "Run trivy fs --format cyclonedx"

  parse_sbom:
    type: python
    module: examples.soup.nodes
    function: parse_sbom

  score_risks:
    type: python
    module: examples.soup.nodes
    function: score_risks

  write_outputs:
    type: python
    module: examples.soup.nodes
    function: write_outputs

nodes:
  generate_sbom:
    type: python
    tool: generate_sbom

  parse_sbom:
    type: python
    tool: parse_sbom

  score_risks:
    type: python
    tool: score_risks

  generate_narratives:
    type: llm
    prompt: prompts/narratives
    state_key: narratives

  write_outputs:
    type: python
    tool: write_outputs

edges:
  - from: START
    to: generate_sbom
  - from: generate_sbom
    to: parse_sbom
  - from: parse_sbom
    to: score_risks
  - from: score_risks
    to: generate_narratives
  - from: generate_narratives
    to: write_outputs
  - from: write_outputs
    to: END
```

## Risk Scoring Policy

| Risk Type | Indicators | Source |
|-----------|------------|--------|
| **Security** | Critical/High CVEs | Trivy/OSV-Scanner |
| **Maintenance** | No release in N months | PyPI metadata |
| **License** | Copyleft vs permissive | SBOM license field |
| **Criticality** | Runtime vs dev dependency | pyproject.toml groups |

## Why This Approach Wins

| Approach | Credibility | Differentiation | Effort |
|----------|-------------|-----------------|--------|
| ❌ Reimplement SBOM | Low | None | High |
| ❌ SBOM tools only | High | None | Low |
| ✅ **Hybrid** | High ("we use standard SBOM") | High ("we add narratives + policy") | Medium |

## Acceptance Criteria

- [ ] Uses real SBOM tool (Trivy) as first step
- [ ] Parses CycloneDX into normalized component list
- [ ] Applies configurable risk policy
- [ ] LLM generates doc-ready narratives
- [ ] Outputs standard SBOM + enriched report
- [ ] PoC runs against YAMLGraph repo
- [ ] README documents Trivy prerequisite

## Prerequisites

```bash
# Install Trivy (macOS)
brew install trivy

# Or via Docker
docker pull aquasec/trivy
```

## Related

- [examples/codegen/](../examples/codegen/) - Tool-heavy pipeline with shell nodes
- [examples/beautify/](../examples/beautify/) - LLM analysis + structured output
- [examples/book_translator/](../examples/book_translator/) - Map nodes for parallel work
