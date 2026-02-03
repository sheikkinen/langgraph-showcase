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
