# Quick Start Guide

Create your first YAML-based LLM pipeline in 5 minutes.

---

## Step 1: Create a Prompt

Create `prompts/my_prompt.yaml`:

```yaml
schema:
  name: Greeting
  fields:
    message:
      type: str
      description: "The greeting message"
    mood:
      type: str
      description: "Detected mood: happy, neutral, or formal"

system: |
  You are a friendly greeter. Generate personalized greetings.

user: |
  Create a {style} greeting for someone named {name}.
```

---

## Step 2: Create a Graph

Create `graphs/my_pipeline.yaml`:

```yaml
version: "1.0"
name: my-pipeline
description: Simple greeting generator

defaults:
  provider: mistral
  temperature: 0.7

nodes:
  greet:
    type: llm
    prompt: my_prompt
    variables:
      name: "{state.name}"
      style: "{state.style}"
    state_key: greeting

edges:
  - from: START
    to: greet
  - from: greet
    to: END
```

---

## Step 3: Run It

```bash
showcase graph run graphs/my_pipeline.yaml --var name="Alice" --var style="formal"
```

Or programmatically:

```python
from showcase.graph_loader import load_and_compile

graph = load_and_compile("graphs/my_pipeline.yaml")
app = graph.compile()

result = app.invoke({
    "name": "Alice",
    "style": "formal"
})

print(result["greeting"].message)
```

---

## Step 4: Extend It

### Add a Second Node

```yaml
nodes:
  greet:
    type: llm
    prompt: my_prompt
    variables:
      name: "{state.name}"
      style: "{state.style}"
    state_key: greeting

  analyze:
    type: llm
    prompt: analyze_greeting
    variables:
      message: "{state.greeting.message}"
    state_key: analysis
    requires: [greeting]

edges:
  - from: START
    to: greet
  - from: greet
    to: analyze
  - from: analyze
    to: END
```

### Add Error Handling

```yaml
nodes:
  greet:
    type: llm
    prompt: my_prompt
    on_error: fallback
    fallback:
      provider: anthropic
    # ... rest of config
```

### Add Routing

```yaml
nodes:
  classify:
    type: router
    prompt: classify_style
    routes:
      formal: formal_greeter
      casual: casual_greeter
    default_route: casual_greeter
    variables:
      style: "{state.style}"
    state_key: classification

  formal_greeter:
    type: llm
    prompt: formal_greet
    # ...

  casual_greeter:
    type: llm
    prompt: casual_greet
    # ...

edges:
  - from: START
    to: classify
  - from: classify
    to: [formal_greeter, casual_greeter]
    type: conditional
  - from: formal_greeter
    to: END
  - from: casual_greeter
    to: END
```

---

## Directory Structure

```
my-project/
├── graphs/
│   └── my_pipeline.yaml      # Graph definitions
├── prompts/
│   ├── my_prompt.yaml        # Main prompts
│   └── router-demo/          # Grouped prompts
│       ├── classify.yaml
│       └── respond.yaml
└── showcase/
    └── models/
        └── state.py          # Custom state if needed
```

---

## Common Tasks

### Access Nested State

```yaml
variables:
  content: "{state.generated.content}"
  first_tag: "{state.analysis.tags}"  # Lists auto-join
```

### Use Jinja2 Templates

```yaml
template: |
  {% for item in items %}
  - {{ item.title }}
  {% endfor %}
```

### Add Loop Limits

```yaml
loop_limits:
  critique: 3

nodes:
  critique:
    skip_if_exists: false  # Required for loops
```

### Export Results

```yaml
exports:
  summary:
    format: markdown
    filename: output.md
```

---

## Next Steps

- [Graph YAML Reference](graph-yaml.md) - All graph configuration options
- [Prompt YAML Reference](prompt-yaml.md) - Schema and template details
- [Common Patterns](patterns.md) - Router, loops, agents, and more

---

## Troubleshooting

### "Missing required state: X"

Add the dependency to `requires`:
```yaml
requires: [generated, analysis]
```

### "Prompt not found"

Check prompt path matches:
- Graph: `prompt: router-demo/classify`
- File: `prompts/router-demo/classify.yaml`

### Loop runs forever

Add `loop_limits` and set `skip_if_exists: false`:
```yaml
loop_limits:
  my_node: 5

nodes:
  my_node:
    skip_if_exists: false
```

### Router goes to wrong node

Check the `routes` map matches your schema's field values:
```yaml
# Schema returns: tone: "positive"
routes:
  positive: handle_positive   # Key must match value
  negative: handle_negative
```
