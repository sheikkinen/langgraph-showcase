# Intent + Questionnaire Pattern

This document describes the pattern for handling dynamic intent-based routing between questionnaires with proper session management.

---

## Problem

In a multi-questionnaire system where an intent detector (e.g., "navigator") routes users to specialized questionnaires (e.g., "booking-fi", "phq9", "audit"), the following issues arise:

1. **Stale Session References** - After reroute, the client still holds the original session ID and template
2. **Isolated Keyspaces** - Each template stores state under its own Redis prefix (`navigator:*`, `booking-fi:*`)
3. **Lost Context** - Returning to the old session causes the conversation to regress

### Failing Scenario

```
User → navigator (session: web-abc, template: navigator)
  ↓ intent detected: "ajanvaraus"
User → booking-fi (session: web-abc-r1, template: booking-fi)
  ↓ user's next message uses stale values
User → navigator (session: web-abc, template: navigator)  ← WRONG!
```

---

## Prerequisites

This pattern requires:

1. **A graph-based session system** that returns structured results including a `status` field
2. **Redis** for cross-request state (registry + phone mapping)
3. **Intent detection** in the "navigator" graph that emits `reroute` status

### Intent Detection Output

The navigator graph must return this structure when detecting an intent change:

```python
# From yamlgraph session's process_message()
InterviewResponse(
    status="reroute",           # Triggers reroute handling
    result={
        "new_intent": "ajanvaraus",       # Intent name
        "trigger_message": "haluan varata ajan",  # User's message
        "portable_state": {...},          # Optional context to carry over
    },
    ...
)
```

---

## Solution: Unified Session Registry

A Redis-based registry that maps base session IDs to their currently active session, enabling the server to follow reroute chains regardless of what the client sends.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Session Registry                      │
│  session:registry:{base_id} → {                         │
│    active_session_id: "web-abc-r1",                     │
│    active_template: "booking-fi",                       │
│    reroute_chain: [                                     │
│      {session_id: "web-abc", template: "navigator"},    │
│      {session_id: "web-abc-r1", template: "booking-fi"} │
│    ],                                                   │
│    updated_at: "2026-02-05T12:00:00"                    │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
                         ▲
                         │ lookup before loading graph
                         │
┌────────────────────────┴────────────────────────────────┐
│                  Request Flow                            │
│                                                          │
│  1. Client sends: session_id="web-abc", template="nav"  │
│  2. Server: get_base_session_id("web-abc") → "web-abc"  │
│  3. Server: get_active_session("web-abc")               │
│     → {active: "web-abc-r1", template: "booking-fi"}    │
│  4. Server: load graph for "booking-fi" (not "nav")     │
│  5. Server: process message in "web-abc-r1"             │
│  6. Response includes actual session_id and template    │
└─────────────────────────────────────────────────────────┘
```

### Key Insight

**The server is authoritative.** Clients can send stale session/template values—the server follows the registry regardless.

---

## Implementation

### 1. Session Registry Module

```python
# src/api/session_registry.py

REGISTRY_TTL = 86400  # 24 hours
MAX_REROUTE_CHAIN = 5  # Prevent infinite reroute loops

@dataclass
class RerouteEntry:
    session_id: str
    template: str

@dataclass
class SessionRegistryEntry:
    active_session_id: str
    active_template: str
    reroute_chain: list[RerouteEntry]
    updated_at: str

def get_base_session_id(session_id: str) -> str:
    """Strip reroute suffix: 'web-abc-r1' → 'web-abc'"""
    return re.sub(r"-r\d+$", "", session_id)

async def get_active_session(request, session_id) -> Optional[SessionRegistryEntry]:
    """Lookup registry by base session ID."""
    ...

async def set_active_session(request, session_id, template, previous_entry=None) -> bool:
    """Update registry. Returns False if reroute limit exceeded."""
    ...

async def clear_session_registry(request, session_id) -> list[RerouteEntry]:
    """Clear on completion. Returns chain for cleanup."""
    ...
```

### 2. Intent-to-Template Mapping

Map intent names from the navigator to actual template names:

```python
# At module level in the route file
INTENT_TO_TEMPLATE = {
    "elderlycare": "interrai-ca",
    "depression": "phq9",
    "alcohol": "audit",
    "ajanvaraus": "booking-fi",
    "crisis": "navigator",  # Stay in navigator for crisis handling
}
```

### 3. Session ID Suffix Generator

```python
REROUTE_SUFFIX_PATTERN = re.compile(r"-r(\d+)$")

def _get_rerouted_session_id(session_id: str) -> str:
    """Get new session ID with incremented reroute suffix.

    Examples:
        "session-abc" -> "session-abc-r1"
        "session-abc-r1" -> "session-abc-r2"
    """
    match = REROUTE_SUFFIX_PATTERN.search(session_id)
    if match:
        current_num = int(match.group(1))
        base = session_id[: match.start()]
        return f"{base}-r{current_num + 1}"
    return f"{session_id}-r1"
```

### 4. Session Resolution Function

```python
@dataclass
class ResolvedSession:
    session_id: str
    template: str
    followed_reroute: bool
    resumed_from_phone: bool
    registry_entry: Optional[SessionRegistryEntry]

async def _resolve_session(
    request: Request,
    payload_session_id: str,
    payload_template: str,
    sms_to: Optional[str],
) -> ResolvedSession:
    """Resolve effective session BEFORE loading graph.

    Priority:
    1. Registry (follows reroute chain)
    2. Phone mapping (for SMS/voice resume)
    3. Payload values (new session)
    """
    # Check registry first
    registry_entry = await get_active_session(request, payload_session_id)

    if registry_entry:
        # Registry found - follow reroute if different
        if (registry_entry.active_session_id != payload_session_id
            or registry_entry.active_template != payload_template):
            return ResolvedSession(
                session_id=registry_entry.active_session_id,
                template=registry_entry.active_template,
                followed_reroute=True,
                ...
            )

    # No registry - check phone mapping for SMS resume
    if sms_to:
        mapping = await lookup_session_by_phone(request, sms_to)
        if mapping:
            return ResolvedSession(
                session_id=mapping.session_id,
                template=mapping.template,
                resumed_from_phone=True,
                ...
            )

    # New session - use payload values
    return ResolvedSession(...)
```

### 5. Route Integration

```python
# Graph cache for performance (load once per template)
_graph_cache: dict[str, CompiledGraph] = {}

async def _get_graph_app(template: str) -> CompiledGraph:
    """Get cached graph app for template."""
    if template not in _graph_cache:
        _graph_cache[template] = build_graph(template)
    return _graph_cache[template]

async def questionnaire_assessment(request, payload, _):
    # === STEP 1: Resolve BEFORE loading graph ===
    resolved = await _resolve_session(
        request, payload.session_id, payload.template, payload.sms_to
    )

    # === STEP 2: Load correct graph (once!) ===
    app = await _get_graph_app(resolved.template)

    # === STEP 3: Create session ===
    session = YamlGraphInterviewSession(
        app=app,
        thread_id=resolved.session_id,
        template_name=resolved.template,
    )

    # === STEP 3b: Check if resumed session is already complete ===
    if resolved.resumed_from_phone or resolved.followed_reroute:
        state = await session.get_state()
        if state and state.get("is_complete", False):
            # Session complete - start fresh with payload values
            resolved = ResolvedSession(
                session_id=payload.session_id,
                template=payload.template,
                followed_reroute=False,
                resumed_from_phone=False,
                registry_entry=None,
            )
            app = await _get_graph_app(resolved.template)
            session = YamlGraphInterviewSession(...)

    # === STEP 4: Register if new ===
    if not resolved.registry_entry:
        await set_active_session(request, resolved.session_id, resolved.template)

    # === STEP 5: Process message ===
    result = await session.process_message(payload.query)

    # === STEP 6: Handle reroute ===
    if result.status == "reroute":
        new_session_id = _get_rerouted_session_id(resolved.session_id)
        new_intent = result.result.get("new_intent")
        new_template = INTENT_TO_TEMPLATE.get(new_intent, new_intent)
        trigger_message = result.result.get("trigger_message", payload.query)

        # Get current registry for chain building
        current_registry = resolved.registry_entry or await get_active_session(
            request, resolved.session_id
        )

        # Update registry with chain (returns False if limit exceeded)
        if not await set_active_session(
            request, new_session_id, new_template, current_registry
        ):
            # Reroute limit exceeded - stay in current session
            logger.warning("Reroute blocked due to chain limit")
        else:
            # Process in new session
            new_app = await _get_graph_app(new_template)
            new_session = YamlGraphInterviewSession(
                app=new_app, thread_id=new_session_id, template_name=new_template
            )
            result = await new_session.process_message(trigger_message)
            effective_session_id = new_session_id
            effective_template = new_template

    # === STEP 7: Cleanup on completion ===
    if result.status == "complete":
        chain = await clear_session_registry(request, resolved.session_id)
        # Optionally cleanup old sessions from checkpointer

    # === STEP 8: Return actual values ===
    return QuestionnaireResponse(
        session_id=effective_session_id,
        template=effective_template,  # Actual template used
        ...
    )
```

---

## Session ID Suffix Convention

Rerouted sessions get an incrementing suffix:

| Event | Session ID |
|-------|------------|
| Initial | `web-abc` |
| 1st reroute | `web-abc-r1` |
| 2nd reroute | `web-abc-r2` |
| Base ID | `web-abc` (always) |

This allows:
- Unique session IDs per graph instance
- Registry lookup by base ID
- Chain tracking for cleanup

---

## Reroute Limit Protection

To prevent infinite reroute loops (e.g., navigator → booking → navigator → booking...):

```python
MAX_REROUTE_CHAIN = 5

async def set_active_session(request, session_id, template, previous_entry=None):
    if previous_entry and len(previous_entry.reroute_chain) >= MAX_REROUTE_CHAIN:
        logger.error(f"Reroute limit exceeded")
        return False  # Block reroute
    ...
```

---

## Response Model

Include actual session/template in response for client awareness:

```python
class QuestionnaireResponse(BaseModel):
    response: str
    phase: str
    is_complete: bool
    session_id: Optional[str]   # Actual session (may differ from request)
    template: Optional[str]     # Actual template (may differ from request)
    resumed: bool
    ...
```

---

## Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Server is authoritative** | Registry determines session, not client payload |
| **Resolve before load** | Check registry BEFORE loading any graph |
| **Single graph load** | Only load the effective template's graph |
| **Chain tracking** | Keep history for cleanup and debugging |
| **Fail open** | Registry errors don't block requests |
| **Cleanup on complete** | Clear registry and old sessions |

---

## Testing Strategy

### Unit Tests

```python
class TestGetBaseSessionId:
    def test_no_suffix(self):
        assert get_base_session_id("web-abc") == "web-abc"

    def test_with_suffix(self):
        assert get_base_session_id("web-abc-r3") == "web-abc"

class TestResolveSession:
    async def test_follows_registry_reroute(self):
        """Registry shows reroute - should follow it."""
        registry_entry = SessionRegistryEntry(
            active_session_id="web-abc-r1",
            active_template="booking-fi",
            ...
        )
        resolved = await _resolve_session(request, "web-abc", "navigator", None)
        assert resolved.session_id == "web-abc-r1"
        assert resolved.template == "booking-fi"
        assert resolved.followed_reroute is True
```

### Integration Test

```bash
# 1. Start navigator session
curl -X POST /questionnaire -d '{"session_id":"test-123","template":"navigator","query":"hello"}'

# 2. Trigger reroute
curl -X POST /questionnaire -d '{"session_id":"test-123","template":"navigator","query":"haluan varata ajan"}'
# Response: session_id="test-123-r1", template="booking-fi"

# 3. Continue with stale values (server should follow registry)
curl -X POST /questionnaire -d '{"session_id":"test-123","template":"navigator","query":"next message"}'
# Response: session_id="test-123-r1", template="booking-fi" (followed reroute!)
```

---

## Related Files

- [src/api/session_registry.py](../src/api/session_registry.py) - Registry module
- [src/api/routes/questionnaire.py](../src/api/routes/questionnaire.py) - Route with `_resolve_session`
- [src/api/phone_session.py](../src/api/phone_session.py) - Phone-to-session mapping for SMS resume
- [tests/api/test_session_registry.py](../tests/api/test_session_registry.py) - Registry tests
- [tests/api/test_resolve_session.py](../tests/api/test_resolve_session.py) - Resolution tests
- [docs/plan-session-rerouting.md](plan-session-rerouting.md) - Original implementation plan

---

## Checklist for New Projects

When implementing this pattern in a new project:

- [ ] Implement `InterviewResponse` with `status` field including `"reroute"` value
- [ ] Navigator graph detects intent and returns `{new_intent, trigger_message}`
- [ ] Create `session_registry.py` with registry functions
- [ ] Create `INTENT_TO_TEMPLATE` mapping for your questionnaires
- [ ] Add `_resolve_session()` that checks registry BEFORE loading graph
- [ ] Add `_get_rerouted_session_id()` suffix generator
- [ ] Integrate registry into route: resolve → load → register → process → reroute → cleanup
- [ ] Return actual `session_id` and `template` in response
- [ ] Add Redis connection to app state
- [ ] Write tests for registry and resolution functions
