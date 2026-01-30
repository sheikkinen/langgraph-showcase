# Example Request: SOUP Doc Compiler for SaMD/MDSW

**Priority:** MEDIUM  
**Type:** Example + Potential Product  
**Status:** Proposed  
**Effort:** 3–4 days  
**Requested:** 2026-01-30

## Summary

Create a SOUP documentation pipeline (`examples/soup/`) aligned with **IEC 62304** requirements for SaMD/MDSW. Uses real SBOM tools (Trivy/Syft) for extraction, YAMLGraph for policy scoring, classification, LLM narratives, and audit-ready exports.

**Business case**: This could be a differentiating feature for a **dual-licensed YAMLGraph SaMD Edition**.

## Business Model: Dual Licensing

| Edition | License | SOUP Tools | Target |
|---------|---------|------------|--------|
| **YAMLGraph Core** | MIT (AS-IS) | Not included | General users |
| **YAMLGraph SaMD** | Commercial | ✅ Included + validated | Regulated software teams |

### What SaMD Edition Could Include

| Feature | Value |
|---------|-------|
| **SOUP Doc Compiler** | IEC 62304-aligned SOUP documentation |
| **Pre-validated examples** | Interrupt patterns, checkpointing for audit trail |
| **Verification evidence** | Test reports, known limitations documented |
| **Support SLA** | Response time commitments for regulated use |
| **Training materials** | SaMD-specific usage guidance |

### Pricing Considerations

| Model | Price Point | Notes |
|-------|-------------|-------|
| Per-project license | $500–2,000 | One-time per regulatory submission |
| Annual subscription | $2,000–5,000 | Unlimited projects, updates included |
| Consulting bundle | $5,000+ | License + setup + customization |

## IEC 62304 Alignment

### SOUP Requirements (§8.1.2)

For each SOUP item, IEC 62304 requires:

| Requirement | What Pipeline Produces |
|-------------|------------------------|
| **8.1.2.a** - Identify title, manufacturer, version | ✅ From SBOM |
| **8.1.2.b** - Document requirements | ⚠️ LLM-assisted draft |
| **8.1.2.c** - Document known anomalies | ✅ CVE data from Trivy |
| **8.1.2.d** - Evaluate anomaly impact | ⚠️ LLM risk narrative + human review |

### SOUP Classification (Class A/B/C)

| Class | Criteria | Pipeline Output |
|-------|----------|-----------------|
| **A** | No contribution to hazard | `safety_relevant: false` |
| **B** | Contribution to hazard, not serious | `safety_relevant: true, severity: low` |
| **C** | Could contribute to death/serious injury | `safety_relevant: true, severity: high` |

## Architecture: Hybrid Approach

### Layer 1: SBOM Tools (External)

| Tool | Purpose |
|------|---------|
| **Trivy** | SBOM generation (`--format cyclonedx`) + vulnerability scan |
| **OSV-Scanner** | Dependency-to-vuln matching |

### Layer 2: YAMLGraph (Differentiated Value)

| Capability | IEC 62304 Relevance |
|------------|---------------------|
| **Parse + normalize** | Component inventory |
| **Classification** | Safety-relevant Y/N, software class |
| **Known anomalies** | CVE data + severity |
| **Risk narratives** | LLM-generated assessment drafts |
| **Human review** | Interrupt node for classification approval |
| **Export doc pack** | MD/JSON/CSV for QMS import |

## Pipeline Design

### Nodes

| Node | Type | Description |
|------|------|-------------|
| `generate_sbom` | python | Run `trivy fs --format cyclonedx` |
| `parse_sbom` | python | Parse CycloneDX → normalized components |
| `classify_components` | python | Mark runtime/dev, safety-relevant. Dev-only dependencies don’t belong in SOUP documentation. |
| `score_risks` | python | CVE severity, maintenance risk |
| `review_classification` | interrupt | Human approves safety classification |
| `generate_narratives` | llm | IEC 62304-aligned risk narrative |
| `write_outputs` | python | Export doc pack |

### Outputs

| File | Purpose | QMS Use |
|------|---------|---------|
| `sbom.json` | Standard CycloneDX | Attach to technical file |
| `soup_inventory.csv` | Structured component list | Import to Jama/Polarion |
| `soup_report.md` | Human-readable narratives | Review + approval |
| `soup_classification.json` | Class A/B/C per component | Audit evidence |

### Example Graph (Sketch)

```yaml
version: "1.0"
name: soup_compiler

state:
  target_path: str
  risk_profile: str  # e.g., "Class B medical device"
  safety_contribution: str  # none | indirect | direct
  severity_assessment: str  # low | medium | high
  sbom_path: str
  components: list
  classified: list
  scored: list
  narratives: dict
  approved: bool
  narrative_confidence: str  # low | medium | high

nodes:
  generate_sbom:
    type: python
    tool: generate_sbom

  parse_sbom:
    type: python
    tool: parse_sbom

  classify_components:
    type: python
    tool: classify_components

  score_risks:
    type: python
    tool: score_risks

  review_classification:
    type: interrupt
    prompt: "Review SOUP classification. Approve safety-relevant assignments."

  generate_narratives:
    type: llm
    prompt: prompts/soup_narratives
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
    to: classify_components
  - from: classify_components
    to: score_risks
  - from: score_risks
    to: review_classification
  - from: review_classification
    to: generate_narratives
  - from: generate_narratives
    to: write_outputs
  - from: write_outputs
    to: END
```

## Competitive Positioning

| Solution | Cost | IEC 62304? | Narratives? | YAMLGraph? |
|----------|------|------------|-------------|------------|
| Excel + ChatGPT | Free | Manual | Manual | No |
| Trivy + template | Free | Partial | No | No |
| **YAMLGraph SaMD** | $$ | ✅ Aligned | ✅ LLM | ✅ |
| Jama/Polarion | $$$$ | ✅ | Template | No |
| MedCrypt | $$$ | ✅ | Partial | No |

## Acceptance Criteria

- [ ] Uses Trivy for SBOM generation
- [ ] Parses CycloneDX into normalized components
- [ ] Classifies components as safety-relevant (Y/N)
- [ ] Assigns software class (A/B/C) per component
- [ ] Documents known anomalies from CVE data; CVE → hazard linkage analysis → severity evaluation → risk control documentation
- [ ] Human review interrupt for classification approval
- [ ] LLM generates IEC 62304-style risk narratives
- [ ] Outputs CSV importable to QMS tools
- [ ] PoC runs against YAMLGraph repo
- [ ] README documents regulatory context (not claims)

## Disclaimers (Required for SaMD Edition)

```
DISCLAIMER: This tool assists with SOUP documentation. It does not
guarantee regulatory compliance. All outputs require human review
and approval by qualified personnel. The tool is not validated
software and must not be used as the sole basis for regulatory
submissions without independent verification.

Tool qualification responsibility lies with the manufacturer per
IEC 62304 and applicable regulations. YAMLGraph SaMD edition
maintains versioning and change logs for traceability.

NOTE: LLM-generated narratives are non-deterministic. Outputs may
vary between runs. Always review and approve narratives before
including in regulatory submissions.
```

## Prerequisites

```bash
# Install Trivy
brew install trivy

# Or via Docker
docker pull aquasec/trivy
```

## Related

- [examples/beautify/](../examples/beautify/) - LLM analysis + structured output
- [examples/booking/](../examples/booking/) - Interrupt patterns for human review
- [examples/codegen/](../examples/codegen/) - Tool-heavy pipeline
