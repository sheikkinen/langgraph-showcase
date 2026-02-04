# Router Demo

Routes responses based on detected message tone (positive/negative/neutral).

## Usage

```bash
yamlgraph graph run examples/demos/router/graph.yaml \
  --var message="I absolutely love this product!"
```

Try different tones:

```bash
# Negative
yamlgraph graph run examples/demos/router/graph.yaml \
  --var message="This is terrible, I'm so frustrated"

# Neutral
yamlgraph graph run examples/demos/router/graph.yaml \
  --var message="Can you tell me the store hours?"
```

## What It Does

1. **Classifies** the message tone using LLM
2. **Routes** to appropriate response node based on classification
3. **Responds** with tone-appropriate message

## Pipeline

```
         ┌→ respond_positive ─┐
START → classify ─┼→ respond_negative ─┼→ END
         └→ respond_neutral ──┘
```

## Key Concepts

- **`type: router`** - Conditional routing node
- **`routes`** - Map of classification values to target nodes
- **`default_route`** - Fallback when classification doesn't match

## Router Node Configuration

```yaml
classify:
  type: router
  prompt: classify_tone
  routes:
    positive: respond_positive
    negative: respond_negative
    neutral: respond_neutral
  default_route: respond_neutral
```

## Learning Path

After [hello](../hello/). Next: [map](../map/) for parallel processing.
