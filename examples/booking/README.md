# Booking Example

A conversational appointment booking system demonstrating YAMLGraph with FastAPI.

## Features

- 🗓️ **FHIR-inspired API**: Calendar → Slot → Appointment resources
- 💬 **Conversational booking**: LangGraph with interrupt support
- 🔧 **Tool nodes**: `check_availability`, `book_slot` callable from graph
- 🚀 **Fly.io ready**: SQLite + volume mount, redis-simple checkpointer

## Quick Start

### CLI Demo (No server)
```bash
python examples/booking/run_booking.py
```

### API Server
```bash
# Install dependencies
pip install -e ".[booking]"

# Run locally
uvicorn examples.booking.main:app --reload

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/calendars
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/calendars` | Create calendar |
| GET | `/calendars` | List calendars |
| GET | `/calendars/{id}` | Get calendar |
| DELETE | `/calendars/{id}` | Delete calendar |
| POST | `/calendars/{id}/slots` | Create slot |
| GET | `/calendars/{id}/slots?available=true` | List slots |
| GET | `/slots/{id}` | Get slot |
| DELETE | `/slots/{id}` | Delete slot |
| POST | `/appointments` | Book appointment |
| GET | `/appointments` | List appointments |
| GET | `/appointments/{id}` | Get appointment |
| PATCH | `/appointments/{id}/cancel` | Cancel |
| DELETE | `/appointments/{id}` | Delete |
| POST | `/chat/{thread_id}` | Start chat |
| POST | `/chat/{thread_id}/resume` | Resume after interrupt |
| GET | `/health` | Health check |

## Testing

### Unit Tests
```bash
# Run all tests
pytest examples/booking/tests/ -v

# Run specific test file
pytest examples/booking/tests/test_api_db.py -v
```

### E2E Test Script
```bash
# Run complete end-to-end test (starts server, seeds data, tests API & chat)
./examples/booking/scripts/e2e_booking.sh
```

The E2E script tests:
- ✅ Server startup and health check
- ✅ Database seeding with calendars/slots
- ✅ **Calendar status display** (shows slots and bookings)
- ✅ REST API endpoints
- ✅ Chat conversation flow (name → slot selection → booking)
- ✅ **Booking verification in database**
- ✅ **Post-booking calendar status** (shows slot availability changes)
- ✅ Unit test suite

### Manual Chat Testing
```bash
# Start server
uvicorn examples.booking.main:app --reload --port 8001

# Seed data
./examples/booking/scripts/seed_calendar.sh

# Start chat
curl -X POST http://localhost:8001/chat/test123 \
  -H "Content-Type: application/json" \
  -d '{"message": "start"}'

# Resume with name
curl -X POST http://localhost:8001/chat/test123/resume \
  -H "Content-Type: application/json" \
  -d '{"answer": "John Doe"}'

# Select slot (use slot ID from previous response)
curl -X POST http://localhost:8001/chat/test123/resume \
  -H "Content-Type: application/json" \
  -d '{"answer": "slot_xxx"}'

# Verify booking was created
curl http://localhost:8001/appointments/{booking_id}

# Check calendar status (slots and bookings)
curl http://localhost:8001/calendars
curl http://localhost:8001/calendars/{calendar_id}/slots
curl http://localhost:8001/appointments
```

## Deployment (Fly.io)

```bash
cd examples/booking

# Create app
fly apps create yamlgraph-booking

# Create volume for SQLite
fly volumes create booking_data --size 1 --region iad

# Set secrets
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly secrets set UPSTASH_REDIS_URL=redis://...

# Deploy
fly deploy
```

## Architecture

```
examples/booking/
├── api/
│   ├── app.py      # FastAPI factory
│   ├── db.py       # SQLite CRUD
│   └── models.py   # Pydantic schemas
├── graphs/
│   └── booking.yaml  # LangGraph definition
├── nodes/
│   └── tools.py    # Tool implementations
├── tests/          # 89 tests
├── main.py         # Entry point
├── fly.toml        # Fly.io config
└── Dockerfile
```

## Graph Flow

```
START → greet → await_request → check_slots → present_slots
                                                    ↓
               END ← farewell ← confirm_booking ← await_selection
```

## Tests

```bash
# Run all booking tests
pytest examples/booking/tests/ -v

# 89 tests covering:
# - Models (13)
# - Database (16)
# - Routes (36)
# - E2E flows (5)
# - Config (7)
# - Main (5)
# - Graph (12)
```
