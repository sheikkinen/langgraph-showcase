# Booking Assistant

Conversational appointment booking with calendar integration.

## Quick Start

```bash
# Validate graph
yamlgraph graph validate examples/booking/graph.yaml

# Run interactive demo (requires API keys)
python examples/booking/run_booking.py

# Or run single pass with CLI
yamlgraph graph run examples/booking/graph.yaml -v 'service_name=Health Clinic'
```

## Architecture

```
Layer 2: API        FastAPI + WebSocket  (TODO)
Layer 1: Graph      yamlgraph booking flow ✅
```

## Files

| File | Description |
|------|-------------|
| graph.yaml | Core booking conversation flow |
| nodes/schema.py | Pydantic models (Slot, Booking) |
| nodes/slots_handler.py | Tool nodes: check/book slots |
| prompts/*.yaml | LLM prompts (greeting, present_slots, confirmation) |
| api/ | FastAPI server (TODO) |

## Features

- **Interrupt Nodes**: Multi-turn conversation with user input
- **Tool Nodes**: check_availability, book_slot handlers
- **State Management**: Tracks slots, selection, booking details
- **Provider**: Mistral (configurable)

## Graph Flow

```
START → greet → await_request → check_slots → present_slots
                                                    ↓
                               END ← farewell ← confirm_booking ← await_selection
```

