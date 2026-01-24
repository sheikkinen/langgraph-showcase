# Graph Flow - YAMLGraph Generator

> Flow diagrams and state schema.

## Phase 1 Flow (snippet-based, no fix loop)

```
START
  │
  ▼
┌─────────────────────────────┐
│  classify_patterns (router) │
│  Identify pattern combo     │
│  e.g., "router + map"       │
└──────────────┬──────────────┘
               │
       ┌───────┴───────┐
       │               │
   clear match     unclear
       │               │
       ▼               ▼
  load_snippets   clarify_request
  (for patterns)  (ask user)
       │               │
       └───────┬───────┘
               │
               ▼
┌─────────────────────────────┐
│  select_snippets (llm)      │
│  Pick: nodes, edges, scaffold│
│  Stream: "🧩 Selecting..."  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  assemble_graph (llm)       │
│  Compose snippets + adapt   │
│  Stream: "📐 Assembling..." │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  generate_files (agent)     │
│  Write graph + prompts      │
│  Stream: "📝 Writing..."    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  validate_structure (tool)  │
│  Check prompt YAML valid    │
└──────────────┬──────────────┘
               │
       ┌───────┴───────┐
       │               │
   structure OK    structure error
       │               │
       ▼               ▼
   lint_graph     report_error
       │          (show to user)
       │               │
       │               ▼
       │             END
       │          (partial)
       │
       ▼
┌─────────────────────────────┐
│  lint result check          │
└──────────────┬──────────────┘
       │               │
   lint OK        lint errors
       │               │
       ▼               ▼
  report_success  report_errors
  (show files)    (show issues)
       │               │
       ▼               ▼
      END             END
```

## Phase 3 Flow (adds execution validation)

After lint passes, optionally run:

```
       │
       ▼
┌─────────────────────────────┐
│  run_graph (tool)           │
│  Execute with test inputs   │
│  Full LLM execution         │
└──────────────┬──────────────┘
       │               │
   run OK         run errors
       │               │
       ▼               ▼
  report_success  report_errors
```

## State Schema

See full schema: [samples/state_schema.yaml](samples/state_schema.yaml)

```yaml
state:
  # Input
  request: str              # User's natural language description
  output_dir: str           # Target directory for generated files

  # Classification (snippet-based)
  patterns: list            # Identified patterns: ["router", "map"], etc.
  confidence: float         # Classification confidence (0-1)
  clarification: str        # User's response if patterns were unclear

  # Snippet selection
  selected_snippets: dict   # {category: [snippet_names]}
  snippet_contents: dict    # {snippet_name: content}
  scaffold: str             # Selected scaffold

  # Assembly
  assembled_graph: str      # Composed graph.yaml from snippets
  node_list: list           # List of nodes needing prompts

  # Generated files
  generated_graph: str      # Final graph.yaml content
  generated_prompts: list   # [{filename, content, explanation}]
  generated_tools: list     # [{filename, content, explanation}] (if needed)

  # Validation
  structure_valid: bool     # Prompt YAML structure check
  structure_errors: list    # Any prompt structure issues
  lint_result: dict         # {valid: bool, errors: list}
  run_result: dict          # {valid: bool, output: str, errors: list}

  # Output
  files_written: list       # Paths of all written files
  status: str               # success | partial | failed
  error_summary: str        # Human-readable error description
```

## CLI Usage

```bash
# Generate a router pipeline
yamlgraph graph run examples/yamlgraph-generator/graph.yaml \
  --var request="Create a customer support router that classifies inquiries" \
  --var output_dir="./my-support-bot"

# Generate a batch processor
yamlgraph graph run examples/yamlgraph-generator/graph.yaml \
  --var request="Process a list of URLs, fetch each page, extract the title" \
  --var output_dir="./url-processor"
```

## Related Documents

- [02-snippets.md](02-snippets.md) - Snippet architecture
- [04-assembly-rules.md](04-assembly-rules.md) - Assembly rules
- [samples/state_schema.yaml](samples/state_schema.yaml) - Full state schema
