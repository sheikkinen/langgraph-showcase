# Feature Request Questionnaire Example

**Goal:** Demonstrate the questionnaire pattern (open → probe → recap → analyze → save) in a minimal, self-contained YamlGraph example.

**Use Case:** Collect feature request information interactively, analyze quality, save to markdown file.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Questionnaire Flow                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  START → init → opening → [interrupt] → probe_loop → recap → analyze    │
│                                ↑              │                          │
│                                └──────────────┘                          │
│                              (until all fields)                          │
│                                                                          │
│  analyze → save → closing → END                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Schema (What We Collect)

MVP: 5 required fields (keeps conversation short, ~3-5 turns).

```yaml
# schema.yaml
name: feature-request
description: Collect information for a YamlGraph feature request

# Groups for organized recap display
groups:
  - id: overview
    label: "Overview"
    fields: [title, priority, summary]
  - id: details
    label: "Details"
    fields: [problem, proposed_solution]
  - id: extras
    label: "Additional Info"
    fields: [acceptance_criteria, alternatives]

fields:
  # Required (5 fields - core of any feature request)
  - id: title
    description: Short, descriptive title for the feature
    required: true
    example: "Add data_files directive for loading external YAML"

  - id: priority
    description: Importance level (low, medium, high)
    required: true
    coding:
      low: Not urgent, nice-to-have
      medium: Important but can wait
      high: Critical, blocking work

  - id: summary
    description: Brief 1-2 sentence description
    required: true

  - id: problem
    description: What problem does this solve? Why is it needed?
    required: true

  - id: proposed_solution
    description: How should it work? Include examples if relevant
    required: true

  # Optional (extracted if mentioned, not probed)
  - id: acceptance_criteria
    description: List of criteria to consider the feature complete
    required: false
    extract_as: list

  - id: alternatives
    description: Other approaches that were considered
    required: false
```

---

## File Structure

```
examples/questionnaire/
├── PLAN.md                 # This file
├── README.md               # Usage instructions
├── graph.yaml              # Main questionnaire flow
├── schema.yaml             # Field definitions (loaded via data_files)
├── prompts/
│   ├── opening.yaml        # Initial greeting
│   ├── extract.yaml        # Extract fields from conversation
│   ├── probe.yaml          # Ask about missing fields
│   ├── recap.yaml          # Summarize collected info
│   ├── classify_recap.yaml # Classify user response (confirm/correct/clarify)
│   ├── analyze.yaml        # Critical analysis of the feature request
│   └── closing.yaml        # Farewell with output path
├── tools/
│   └── handlers.py         # Python handlers for state management
└── outputs/                # Generated feature request files (gitignored)
```

---

## Graph Design

### State

```yaml
state:
  # Input
  user_message: str
  skip_opening: bool  # Set when caller already provided greeting

  # Conversation
  messages: list

  # Extraction
  extracted: dict
  gaps: list
  has_gaps: bool
  probe_count: int  # Guard against infinite loops

  # Recap
  recap_action: dict
  recap_summary: str  # Preserved recap for external use
  correction_count: int  # Guard against infinite correction loops

  # Analysis
  analysis: dict

  # Output
  response: str
  phase: str
  complete: bool
  output_path: str
```

### Node Flow

| Phase | Nodes | Purpose |
|-------|-------|---------|
| **Init** | `init` | Initialize state, load schema |
| **Opening** | `opening` → `ask_opening` | Greet user, explain purpose |
| **Probe Loop** | `extract` → `detect_gaps` → `probe` → `ask_probe` | Collect missing fields |
| **Recap** | `recap` → `ask_recap` → `classify` | Confirm collected info |
| **Analyze** | `analyze` | LLM critical analysis of the request |
| **Save** | `save` | Write markdown file |
| **Closing** | `closing` | Farewell with output path |

### Key Patterns

1. **Interrupt nodes** for user input (`ask_opening`, `ask_probe`, `ask_recap`)
2. **Conditional routing** based on `has_gaps`, `probe_count`, and `recap_action`
3. **Max iterations guard** - exit probe loop after 10 turns
4. **Skip opening** - bypass greeting when caller already greeted (`skip_opening`)
5. **Incremental extraction** - pass previous `extracted` to LLM to preserve values
6. **Store recap summary** - preserve recap for external use (email, SMS)
7. **Field groups** - organize schema fields for structured recap display
8. **data_files** for schema loading (no Python needed)
9. **Python tools** for:
   - `append_message` - Conversation management
   - `detect_gaps` - Compare extracted vs schema
   - `apply_corrections` - Merge user corrections into extracted
   - `prune_messages` - Keep context window bounded
   - `store_recap_summary` - Preserve recap for external channels
   - `save_to_file` - Write output markdown

---

## Python Tools (Minimal Set)

```python
# tools/handlers.py
from datetime import date
from pathlib import Path


def append_user_message(state: dict) -> dict:
    """Add user message to conversation history."""
    messages = list(state.get("messages") or [])
    messages.append({"role": "user", "content": state["user_message"]})
    return {"messages": messages}


def append_assistant_message(state: dict) -> dict:
    """Add assistant response to conversation history."""
    messages = list(state.get("messages") or [])
    messages.append({"role": "assistant", "content": state["response"]})
    return {"messages": messages}


def prune_messages(state: dict, max_messages: int = 20) -> dict:
    """Keep conversation within context limits."""
    messages = state.get("messages") or []
    if len(messages) > max_messages:
        # Keep first 2 (opening) + most recent
        messages = messages[:2] + messages[-(max_messages - 2):]
    return {"messages": messages}


def store_recap_summary(state: dict) -> dict:
    """Store recap summary for external use (email, SMS, etc)."""
    response = state.get("response", "")
    return {"recap_summary": response}


def detect_gaps(state: dict) -> dict:
    """Find missing required fields. Increments probe_count."""
    schema = state.get("schema", {})
    extracted = state.get("extracted") or {}
    probe_count = state.get("probe_count", 0) + 1

    gaps = []
    for field in schema.get("fields", []):
        if field.get("required"):
            value = extracted.get(field["id"])
            if value is None or value == "":
                gaps.append(field["id"])

    return {
        "gaps": gaps,
        "has_gaps": len(gaps) > 0,
        "probe_count": probe_count
    }


def apply_corrections(state: dict) -> dict:
    """Merge corrections from recap into extracted data."""
    extracted = dict(state.get("extracted") or {})
    recap_action = state.get("recap_action", {})
    corrections = recap_action.get("corrections", {})
    correction_count = state.get("correction_count", 0) + 1

    for field_id, value in corrections.items():
        if value is not None:
            extracted[field_id] = value

    return {"extracted": extracted, "correction_count": correction_count}


def save_to_file(state: dict) -> dict:
    """Save feature request to markdown file."""
    extracted = state.get("extracted", {})
    analysis = state.get("analysis", {})

    # Generate filename from title
    title = extracted.get("title", "untitled")
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in title.lower())[:50]
    filename = f"{date.today().isoformat()}-{slug}.md"

    # Use CWD/outputs (works with yamlgraph graph run)
    output_dir = Path.cwd() / "outputs"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / filename

    # Format as markdown
    content = format_feature_request(extracted, analysis)
    output_path.write_text(content, encoding="utf-8")

    return {"output_path": str(output_path), "complete": True}


def format_feature_request(extracted: dict, analysis: dict) -> str:
    """Format collected data as feature request markdown."""
    return f'''# Feature Request: {extracted.get("title", "Untitled")}

**Priority:** {extracted.get("priority", "MEDIUM").upper()}
**Type:** Feature
**Status:** Proposed
**Requested:** {date.today().isoformat()}

## Summary

{extracted.get("summary", "")}

## Problem

{extracted.get("problem", "")}

## Proposed Solution

{extracted.get("proposed_solution", "")}

## Acceptance Criteria

{format_list(extracted.get("acceptance_criteria", []))}

## Alternatives Considered

{extracted.get("alternatives", "None documented.")}

## Critical Analysis

{analysis.get("analysis", "")}

### Strengths
{format_list(analysis.get("strengths", []))}

### Concerns
{format_list(analysis.get("concerns", []))}

### Recommendation
{analysis.get("recommendation", "")}
'''


def format_list(items: list) -> str:
    """Format list as markdown bullet points."""
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)
```

---

## Prompts

### opening.yaml

```yaml
system: |
  You are a friendly assistant helping to document a feature request.
  Your goal is to collect all the information needed for a well-structured request.

  Be conversational but efficient. Ask about one or two topics at a time.

user: |
  The user wants to create a feature request. Generate a warm opening that:
  1. Greets them
  2. Explains you'll help them document their idea
  3. Asks them to describe the feature they want

  Keep it to 2-3 sentences.
```

### extract.yaml

```yaml
system: |
  Extract feature request information from the conversation.
  Only extract what is EXPLICITLY stated. Do not infer or assume.
  Preserve previously extracted values unless explicitly changed.

  Fields to extract:
  {% for field in schema.fields %}
  - {{ field.id }}: {{ field.description }}
  {% endfor %}

user: |
  Previously extracted (preserve unless changed):
  {{ extracted | default({}) | tojson(indent=2) }}

  Conversation:
  {% for msg in messages %}
  {{ msg.role }}: {{ msg.content }}
  {% endfor %}

  Extract as JSON with field IDs as keys. Use null for fields not mentioned.
  Keep previous values if not explicitly changed.

output:
  type: object
```

### probe.yaml

```yaml
system: |
  You are helping document a feature request. Some information is still missing.
  Ask about ONE missing field in a natural, conversational way.

  Guidelines:
  - Be specific about what you need
  - Give an example if helpful
  - Keep it brief

user: |
  Missing fields: {{ gaps | join(", ") }}

  {% for field_id in gaps[:1] %}
  {% for field in schema.fields if field.id == field_id %}
  Field details:
  - ID: {{ field.id }}
  - Description: {{ field.description }}
  {% if field.example %}- Example: {{ field.example }}{% endif %}
  {% if field.coding %}- Options: {{ field.coding | tojson }}{% endif %}
  {% endfor %}
  {% endfor %}

  Recent conversation:
  {% for msg in messages[-4:] %}
  {{ msg.role }}: {{ msg.content }}
  {% endfor %}

  Ask about the first missing field naturally.
```

### recap.yaml

```yaml
system: |
  Summarize the feature request information collected so far.
  Present it clearly and ask for confirmation.

user: |
  Collected information:
  {% for field in schema.fields %}
  {% if extracted[field.id] %}
  - **{{ field.id }}**: {{ extracted[field.id] }}
  {% endif %}
  {% endfor %}

  Generate a summary and ask if this is correct, or if they want to change anything.
```

### classify_recap.yaml

```yaml
system: |
  Classify the user's response to the recap summary.

  Options:
  - confirm: User agrees the information is correct
  - correct: User wants to change something
  - clarify: User is confused or asking questions

user: |
  User's response: {{ user_message }}

  Classify and extract any corrections if applicable.

output:
  type: object
  properties:
    action_type:
      type: string
      enum: [confirm, correct, clarify]
    corrections:
      type: object
      description: Field ID to new value mapping for corrections
```

### analyze.yaml

```yaml
system: |
  You are a senior engineer reviewing a feature request.
  Provide critical but constructive analysis.

  Consider:
  - Is the problem clearly defined?
  - Is the solution feasible and well-scoped?
  - Are there missing considerations?
  - What's the implementation risk?

user: |
  Feature Request:

  **Title:** {{ extracted.title }}
  **Priority:** {{ extracted.priority }}

  **Summary:** {{ extracted.summary }}

  **Problem:** {{ extracted.problem }}

  **Proposed Solution:** {{ extracted.proposed_solution }}

  {% if extracted.acceptance_criteria %}
  **Acceptance Criteria:** {{ extracted.acceptance_criteria | join(", ") }}
  {% endif %}

  Provide analysis as JSON.

output:
  type: object
  properties:
    analysis:
      type: string
      description: Overall assessment paragraph
    strengths:
      type: array
      items:
        type: string
    concerns:
      type: array
      items:
        type: string
    recommendation:
      type: string
      enum: [proceed, refine, reconsider]
```

### closing.yaml

```yaml
system: |
  Generate a brief, friendly closing message.

user: |
  The feature request has been saved to: {{ output_path }}

  Analysis recommendation: {{ analysis.recommendation }}

  Generate a 2-3 sentence closing that:
  1. Confirms the file was saved
  2. Mentions the analysis recommendation
  3. Wishes them well
```

---

## Graph (graph.yaml)

```yaml
version: "1.0"
name: feature-request-questionnaire
description: |
  Interactive questionnaire to collect and analyze feature requests.
  Demonstrates: data_files, interrupt nodes, conditional routing, Python tools.

checkpointer:
  type: memory

data_files:
  schema: schema.yaml

prompts_relative: true
prompts_dir: prompts

defaults:
  provider: anthropic
  temperature: 0.7

tools:
  append_user:
    type: python
    module: tools.handlers
    function: append_user_message

  append_assistant:
    type: python
    module: tools.handlers
    function: append_assistant_message

  prune:
    type: python
    module: tools.handlers
    function: prune_messages

  store_recap:
    type: python
    module: tools.handlers
    function: store_recap_summary

  detect_gaps:
    type: python
    module: tools.handlers
    function: detect_gaps

  apply_corrections:
    type: python
    module: tools.handlers
    function: apply_corrections

  save:
    type: python
    module: tools.handlers
    function: save_to_file

nodes:
  # --- Init ---
  init:
    type: passthrough
    output:
      messages: []
      extracted: {}
      gaps: []
      has_gaps: true
      probe_count: 0
      correction_count: 0
      phase: opening

  # --- Opening ---
  opening:
    type: llm
    prompt: opening
    state_key: response

  append_opening:
    type: python
    function: append_assistant

  ask_opening:
    type: interrupt
    state_key: response
    resume_key: user_message

  append_opening_msg:
    type: python
    function: append_user

  # --- Probe Loop ---
  set_probing:
    type: passthrough
    output:
      phase: probing

  extract:
    type: llm
    prompt: extract
    parse_json: true
    variables:
      schema: "{state.schema}"
      messages: "{state.messages}"
      extracted: "{state.extracted}"
    state_key: extracted

  detect_gaps:
    type: python
    function: detect_gaps

  probe:
    type: llm
    prompt: probe
    variables:
      schema: "{state.schema}"
      gaps: "{state.gaps}"
      messages: "{state.messages}"
    state_key: response

  append_probe:
    type: python
    function: append_assistant

  ask_probe:
    type: interrupt
    state_key: response
    resume_key: user_message

  append_probe_msg:
    type: python
    function: append_user

  prune:
    type: python
    function: prune

  # --- Recap ---
  set_recap:
    type: passthrough
    output:
      phase: recap

  recap:
    type: llm
    prompt: recap
    variables:
      schema: "{state.schema}"
      extracted: "{state.extracted}"
    state_key: response

  store_recap:
    type: python
    function: store_recap

  append_recap:
    type: python
    function: append_assistant

  ask_recap:
    type: interrupt
    state_key: response
    resume_key: user_message

  append_recap_msg:
    type: python
    function: append_user

  classify:
    type: llm
    prompt: classify_recap
    parse_json: true
    variables:
      user_message: "{state.user_message}"
    state_key: recap_action

  apply_corrections:
    type: python
    function: apply_corrections

  # --- Analyze ---
  set_analyzing:
    type: passthrough
    output:
      phase: analyzing

  analyze:
    type: llm
    prompt: analyze
    parse_json: true
    variables:
      extracted: "{state.extracted}"
    state_key: analysis

  # --- Save ---
  save:
    type: python
    function: save

  # --- Closing ---
  closing:
    type: llm
    prompt: closing
    variables:
      output_path: "{state.output_path}"
      analysis: "{state.analysis}"
    state_key: response

edges:
  # Init → Opening (skip if caller already greeted)
  - from: START
    to: init
  - from: init
    to: append_opening_msg
    condition: "skip_opening == true"
  - from: init
    to: opening
    condition: "skip_opening != true"
  - from: opening
    to: append_opening
  - from: append_opening
    to: ask_opening
  - from: ask_opening
    to: append_opening_msg
  - from: append_opening_msg
    to: set_probing

  # Probing Loop
  - from: set_probing
    to: extract
  - from: extract
    to: detect_gaps
  - from: detect_gaps
    to: probe
    condition: "has_gaps == true and probe_count < 10"
  - from: detect_gaps
    to: set_recap
    condition: "has_gaps == false or probe_count >= 10"
  - from: probe
    to: append_probe
  - from: append_probe
    to: ask_probe
  - from: ask_probe
    to: append_probe_msg
  - from: append_probe_msg
    to: prune
  - from: prune
    to: extract  # Loop back

  # Recap
  - from: set_recap
    to: recap
  - from: recap
    to: store_recap
  - from: store_recap
    to: append_recap
  - from: append_recap
    to: ask_recap
  - from: ask_recap
    to: append_recap_msg
  - from: append_recap_msg
    to: classify
  - from: classify
    to: set_analyzing
    condition: "recap_action.action_type == 'confirm'"
  - from: classify
    to: set_analyzing
    condition: "correction_count >= 5"  # Force proceed after 5 corrections
  - from: classify
    to: apply_corrections
    condition: "recap_action.action_type == 'correct' and correction_count < 5"
  - from: apply_corrections
    to: recap  # Show updated recap after corrections
  - from: classify
    to: recap  # Explain again
    condition: "recap_action.action_type == 'clarify' and correction_count < 5"

  # Analyze & Save
  - from: set_analyzing
    to: analyze
  - from: analyze
    to: save
  - from: save
    to: closing
  - from: closing
    to: END
```

---

## Implementation Checklist

### Day 1: Core Structure
- [ ] Create `schema.yaml` with field definitions
- [ ] Create `tools/handlers.py` with 6 functions
- [ ] Create basic prompts (`opening.yaml`, `extract.yaml`, `probe.yaml`)
- [ ] Create `graph.yaml` skeleton with init/opening nodes

### Day 2: Probe Loop
- [ ] Implement `detect_gaps` logic
- [ ] Add probe loop edges with conditional routing
- [ ] Test: run graph, verify extraction works

### Day 3: Recap & Analysis
- [ ] Add `recap.yaml` and `classify_recap.yaml`
- [ ] Add `analyze.yaml` for critical analysis
- [ ] Implement recap flow with correction handling

### Day 4: Save & Polish
- [ ] Implement `save_to_file` handler
- [ ] Add `README.md` with usage instructions
- [ ] Test full flow end-to-end
- [ ] Add `.gitignore` for outputs/

---

## Usage

```bash
# Interactive CLI mode
yamlgraph graph run examples/questionnaire/graph.yaml

# With initial input
yamlgraph graph run examples/questionnaire/graph.yaml \
  --var 'user_message=I want to add a data_files directive'

# Resume session
yamlgraph graph run examples/questionnaire/graph.yaml \
  --thread-id my-session --resume "Yes, that looks correct"
```

---

## Success Criteria

- [ ] Collects all required fields through conversation
- [ ] Handles corrections during recap
- [ ] Produces valid markdown matching template format
- [ ] Critical analysis provides actionable feedback
- [ ] Provides closing message with file path and recommendation
- [ ] Can run with `yamlgraph graph run` (no external dependencies)
- [ ] Works with memory checkpointer for session resume
- [ ] Clean separation: schema (data), graph (flow), prompts (LLM), tools (Python)
