# Soul Pattern Example

Demonstrates how to give AI agents consistent personality using the **soul pattern**.

## What is a Soul?

A soul is a configuration file that defines an AI agent's:
- **Name**: Identity
- **Voice**: Communication style
- **Principles**: Core behavioral guidelines
- **Constraints**: Things to avoid

## How It Works

1. **Define a soul** in `souls/friendly.yaml`
2. **Load via `data_files`** in `graph.yaml`
3. **Use in prompts** via Jinja2 templates: `{{ soul.voice }}`

## Files

```
souls/
  friendly.yaml    # Warm, approachable personality
  formal.yaml      # Professional, business-like personality
prompts/
  respond.yaml     # Uses soul in system prompt
graph.yaml         # Loads soul via data_files
```

## Usage

```bash
# Run with default (friendly) soul
yamlgraph run graph.yaml --var 'message=Hello!'

# Switch soul at runtime (input overrides data_files)
yamlgraph run graph.yaml \
  --var 'message=Hello!' \
  --var 'soul={"name": "Custom Bot", "voice": "quirky and fun", "principles": ["be creative"]}'
```

## Key Pattern

```yaml
# graph.yaml
data_files:
  soul: souls/friendly.yaml  # Loaded as state.soul
```

```yaml
# prompts/respond.yaml
system: |
  You are {{ soul.name }}. Your voice is {{ soul.voice }}.

  {% for p in soul.principles %}
  - {{ p }}
  {% endfor %}
```

## Switching Souls

To use a different soul:

1. **At build time**: Change the `data_files.soul` path
2. **At runtime**: Pass `soul` as input (overrides data_files)
3. **Per deployment**: Use different graph files for different personalities
