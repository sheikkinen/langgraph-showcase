# Interview Demo

Human-in-the-loop interview using interrupt nodes.

## Usage

```bash
python scripts/run_interview_demo.py
```

Or via CLI with checkpointer:

```bash
yamlgraph graph run examples/demos/interview/graph.yaml \
  --checkpointer memory --thread-id test123
```

## What It Does

1. Asks user for their name (interrupt)
2. Asks about interests (interrupt)
3. Generates personalized greeting

## Pipeline

```
START → ask_name ⏸ → ask_interests ⏸ → generate_greeting → END
                 ↑                  ↑
              (human input)    (human input)
```

## Key Concepts

- **`type: interrupt`** - Pauses for human input
- **Checkpointer** - Required to resume after interrupt
- **`Command(resume=...)`** - Resume with user input

## Interrupt Node Configuration

```yaml
nodes:
  ask_name:
    type: interrupt
    prompt: ask_name        # Optional prompt before pause
    state_key: user_name    # Where to store response
```

## Requirements

- Checkpointer (memory, sqlite, or redis)
- Thread ID for state persistence

## Learning Path

After [git-report](../git-report/). This shows human-in-the-loop. See [booking](../../booking/) for production interrupt patterns.
