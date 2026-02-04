# FSM Router Example

Demonstrates running YAMLGraph pipelines as statemachine-engine actions.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     statemachine-engine FSM                         │
│                                                                     │
│   waiting ──► classifying ──┬──► simple_response ──► waiting       │
│       ▲                     │                           │           │
│       │                     └──► complex_response ──────┘           │
│       │                                                             │
│       └─────────────────────────────────────────────────────────────┘
│                                                                     │
│   classifying state runs:                                           │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              YAMLGraph classifier.yaml                       │   │
│   │   ┌────────┐                                                 │   │
│   │   │ router │ ─────► returns route: simple | complex | code  │   │
│   │   └────────┘                                                 │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Concept

The FSM orchestrates the workflow. YAMLGraph handles the LLM processing.

1. **FSM** receives a `new_query` event → enters `classifying` state
2. **YAMLGraph** classifier runs → LLM decides route (simple/complex/code)
3. **FSM** transitions to appropriate response state based on route
4. **YAMLGraph** responder generates final response
5. **FSM** returns to `waiting` state

## Files

```
fsm-router/
├── config/
│   └── router.yaml           # FSM state machine config
├── actions/
│   └── yamlgraph_action.py   # Custom action that runs YAMLGraph
├── graphs/
│   ├── classifier.yaml       # Query classification pipeline
│   ├── simple-responder.yaml # Fast response pipeline
│   ├── complex-responder.yaml# Deep analysis pipeline
│   └── prompts/
│       ├── classify.yaml
│       ├── simple-response.yaml
│       ├── complex-analysis.yaml
│       └── complex-response.yaml
├── docs/
│   └── fsm-diagrams/         # Generated Mermaid diagrams for UI
├── tests/
│   └── test_yamlgraph_action.py
└── README.md
```

## Installation

```bash
# From yamlgraph root
pip install -e ".[fsm]"

# Or install statemachine-engine separately
pip install statemachine-engine
```

## Running

### Quick Start

```bash
cd examples/fsm-router

# Generate diagrams for the UI
statemachine-diagrams config/router.yaml --output-dir docs/fsm-diagrams

# Terminal 1: Start the Web UI (includes WebSocket server)
statemachine-ui --port 3001 --project-root .

# Terminal 2: Start the FSM (with env vars for API keys)
source ../../.env  # Ensure MISTRAL_API_KEY is set
statemachine config/router.yaml \
  --machine-name query_router \
  --actions-dir ./actions
```

Open http://localhost:3001 to see the state machine diagram and real-time transitions.

### Start the FSM (Manual)

```bash
cd examples/fsm-router

# Make sure API keys are in environment
export MISTRAL_API_KEY="your-key"

# Start the state machine with custom actions
statemachine config/router.yaml \
  --machine-name query_router \
  --actions-dir ./actions
```

### Send a Query

In another terminal:

```bash
# Simple query → routes to simple_response
statemachine-db send-event \
  --target query_router \
  --type new_query \
  --payload '{"query": "Hello!"}'

# Complex query → routes to complex_response
statemachine-db send-event \
  --target query_router \
  --type new_query \
  --payload '{"query": "Explain the trade-offs between microservices and monoliths"}'

# Code query → routes to complex_response
statemachine-db send-event \
  --target query_router \
  --type new_query \
  --payload '{"query": "How do I implement a binary search tree in Python?"}'
```

### Stop the FSM

```bash
statemachine-db send-event \
  --target query_router \
  --type stop
```

## How It Works

### 1. YamlgraphAction

The `yamlgraph_action.py` is a custom statemachine-engine action:

```python
class YamlgraphAction(BaseAction):
    async def execute(self, context):
        # Load and run YAMLGraph pipeline
        app = await load_and_compile_async(graph_path)
        result = await run_graph_async(app, initial_state)
        
        # Return route event to FSM
        if "route" in result:
            return result["route"]  # Triggers FSM transition
        return success_event
```

### 2. Router Integration

The YAMLGraph `classifier.yaml` uses an LLM node with `output_schema` that returns a `route` field:

```yaml
# classifier.yaml
nodes:
  classify:
    type: llm
    prompt: prompts/classify.yaml
    output_schema:
      route:
        type: string
        enum: [simple, complex, code]
```

The action reads this `route` field and returns it as the FSM event.

### 3. FSM Transitions

The FSM config defines transitions for each possible route:

```yaml
# router.yaml
transitions:
  - from: classifying
    to: simple_response
    event: simple

  - from: classifying
    to: complex_response
    event: complex
```

## Testing

```bash
cd examples/fsm-router
pytest tests/ -v
```

## Why This Pattern?

| Benefit | Description |
|---------|-------------|
| **Separation of concerns** | FSM handles orchestration, YAMLGraph handles LLM |
| **Job queue** | FSM provides SQLite persistence, retries |
| **Multi-machine** | FSM can coordinate multiple workers |
| **Audit trail** | FSM logs all state transitions |
| **LLM flexibility** | YAMLGraph provides multi-provider LLM support |

## When to Use

✅ **Use this when you need:**
- Persistent job queues
- Multi-machine coordination
- Audit trails
- Long-running workflows with LLM steps

❌ **Don't use when:**
- Simple request → LLM → response (just use YAMLGraph alone)
- Already have Celery/Airflow/Temporal

## See Also

- [statemachine-engine docs](https://github.com/sheikkinen/statemachine-engine)
- [YAMLGraph examples](../README.md)
- [FSM + YAMLGraph brainstorming](../../docs-planning/brainstorming-fsm-yamlgraph.md)

## State Groups (for Kanban View)

The FSM config uses state group comments for the UI's Kanban view:

```yaml
states:
  # === IDLE STATES ===
  - waiting

  # === PROCESSING STATES ===
  - classifying
  - simple_response
  - complex_response

  # === COMPLETION STATES ===
  - completed
  - error
```

Run `statemachine-diagrams` to generate the Mermaid diagrams that the UI displays.
