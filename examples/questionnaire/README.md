# Feature Request Questionnaire

Interactive assistant that collects feature request information through a structured conversation, validates completeness, and produces a markdown document with critical analysis.

## Features Demonstrated

- **`data_files`** - Schema loaded from external YAML file at graph compilation
- **Interrupt nodes** - Human-in-the-loop for user input collection
- **Conditional routing** - Loop guards, action-based routing
- **Python tools** - State management functions (handlers)
- **Jinja2 templates** - Dynamic prompts with schema access
- **Probe loop** - Iterative extraction with gap detection
- **Recap flow** - Confirm/correct/clarify cycle

## Quick Start

```bash
# Interactive mode
yamlgraph graph run examples/questionnaire/graph.yaml

# With initial description
yamlgraph graph run examples/questionnaire/graph.yaml \
  --var 'user_message=I want to add URL support for loading remote graphs'

# Resume a session
yamlgraph graph run examples/questionnaire/graph.yaml \
  --thread-id my-session --resume "Yes, that looks correct"
```

## Schema

Collects 5 required fields and 2 optional:

| Field | Required | Description |
|-------|----------|-------------|
| title | ✓ | Short, descriptive title |
| priority | ✓ | low / medium / high |
| summary | ✓ | 1-2 sentence description |
| problem | ✓ | What problem does this solve? |
| proposed_solution | ✓ | How should it work? |
| acceptance_criteria | | List of completion criteria |
| alternatives | | Other approaches considered |

## Flow

```
init → opening → ask → extract → detect_gaps
                                    ↓
                 [has gaps?] ←──── YES: probe → ask_probe → extract
                    ↓ NO
                  recap → ask_recap → classify
                              ↓
                [confirm?] ← YES: analyze → save → closing → END
                    ↓ NO
           [correct?] → apply_corrections → recap (loop)
                    ↓
           [clarify?] → recap (loop)
```

## File Structure

```
examples/questionnaire/
├── graph.yaml          # Main flow definition (25 nodes, 32 edges)
├── schema.yaml         # Field definitions (loaded via data_files)
├── PLAN.md            # Detailed design document
├── README.md          # This file
├── prompts/
│   ├── opening.yaml   # Initial greeting
│   ├── extract.yaml   # Extract fields from conversation
│   ├── probe.yaml     # Ask about missing fields
│   ├── recap.yaml     # Summarize extracted fields
│   ├── classify_recap.yaml  # Classify user response
│   ├── analyze.yaml   # Critical analysis
│   └── closing.yaml   # Final message
├── tools/
│   ├── __init__.py
│   └── handlers.py    # Python handlers (6 functions)
└── tests/
    ├── test_handlers.py         # 16 unit tests
    └── test_graph_integration.py # 15 integration tests
```

## Output

Produces markdown in `outputs/questionnaire/`:

```markdown
# Feature Request: Add URL Support

**Priority:** HIGH
**Type:** Feature
**Status:** Proposed

## Summary
...

## Critical Analysis

### Strengths
- ...

### Concerns
- ...

### Recommendation
proceed / needs_work / reconsider
```

## Testing

```bash
# All tests
pytest examples/questionnaire/tests/ -v

# Unit tests only
pytest examples/questionnaire/tests/test_handlers.py -v

# Integration tests only
pytest examples/questionnaire/tests/test_graph_integration.py -v
```

## Loop Guards

- **Probe loop**: Max 10 iterations (prevents infinite extraction)
- **Correction loop**: Max 5 iterations (prevents infinite corrections)

These guards ensure the conversation terminates even if gaps can't be filled.

---

## Adapting for Other Questionnaires

This example is designed as a **reusable framework**. Most components are generic and schema-driven.

### Component Analysis

| Component | Reusability | Changes Needed |
|-----------|-------------|----------------|
| `graph.yaml` | 95% Generic | Only `name`, `description` |
| `tools/handlers.py` | 90% Generic | Only `_format_*()` function |
| `prompts/extract.yaml` | 100% Generic | None |
| `prompts/probe.yaml` | 100% Generic | None |
| `prompts/recap.yaml` | 95% Generic | Update domain reference |
| `prompts/classify_recap.yaml` | 100% Generic | None |
| `prompts/opening.yaml` | 50% Generic | Update context/persona |
| `prompts/analyze.yaml` | Domain-Specific | Complete rewrite |
| `prompts/closing.yaml` | 80% Generic | Minor adjustments |
| `schema.yaml` | Domain-Specific | Complete rewrite |

### To Create a New Questionnaire

1. **Copy the example:**
   ```bash
   cp -r examples/questionnaire examples/my-questionnaire
   ```

2. **Rewrite `schema.yaml`** with your fields:
   ```yaml
   name: bug-report
   description: Collect information for bug triage

   fields:
     - id: title
       description: Short bug description
       required: true
     - id: severity
       description: critical/major/minor
       required: true
       coding:
         critical: System down
         major: Feature broken
         minor: Cosmetic issue
     - id: steps_to_reproduce
       required: true
     - id: expected_behavior
       required: true
     - id: actual_behavior
       required: true
   ```

3. **Rewrite `prompts/analyze.yaml`** with domain expertise:
   ```yaml
   system: |
     You are a QA engineer triaging a bug report.
     Consider:
     - Is the bug reproducible?
     - What's the blast radius?
     - Is there a workaround?
   ```

4. **Update `prompts/opening.yaml`** system prompt:
   ```yaml
   system: |
     You are helping to document a bug report.
   ```

5. **Rename and update formatter** in `tools/handlers.py`:
   ```python
   def _format_bug_report(extracted: dict, analysis: dict) -> str:
       return f"""# Bug Report: {extracted.get("title")}
   **Severity:** {extracted.get("severity")}
   ...
   """
   ```

6. **Update graph metadata** in `graph.yaml`:
   ```yaml
   name: bug-report-questionnaire
   description: Collect and triage bug reports
   ```

### What Works Unchanged

The following are fully **schema-driven** and require no changes:

- **Extraction loop** — Iterates over `schema.fields` dynamically
- **Gap detection** — Checks `required` fields automatically
- **Probing** — Asks about missing fields from schema
- **Recap** — Displays all collected fields via Jinja2 loop
- **Confirm/Correct/Clarify** — Universal user intent classification
- **Conversation management** — Message append, prune, store

### Example Domains

| Domain | Key Fields |
|--------|------------|
| Bug Report | severity, steps, expected, actual, environment |
| User Interview | goals, pain_points, workflows, feature_wishes |
| Support Ticket | issue_type, urgency, affected_users, workaround |
| Job Application | role, experience, skills, availability, salary |
| Customer Feedback | product, rating, likes, dislikes, suggestions |
