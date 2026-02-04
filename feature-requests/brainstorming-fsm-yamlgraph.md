# Brainstorming: FSM + YAMLGraph Integration

**Date:** 2026-02-04  
**Status:** Exploration  
**Related:** [statemachine-engine](https://github.com/sheikkinen/statemachine-engine)

## Executive Summary

Two YAML-first Python frameworks with complementary strengths:

| Framework | Purpose | Strength |
|-----------|---------|----------|
| **statemachine-engine** | Job orchestration, workflow automation | Event-driven FSM, Unix sockets, SQLite queue |
| **YAMLGraph** | LLM pipelines, AI outputs | DAG execution, structured outputs, multi-provider LLMs |

They operate at different layers of an automation stack and could work together.

---

## Core Integration Concept

**Bidirectional communication loop:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   FSM state change ──► runs YAMLGraph ──► LLM processing                │
│         ▲                                        │                      │
│         │                                        ▼                      │
│         └─────────── FSM transition ◄── sends event                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Direction 1: FSM → YAMLGraph (run pipeline as action)

```yaml
# statemachine-engine transition runs YAMLGraph pipeline
transitions:
  - from: processing
    to: analyzed
    event: done
    actions:
      - type: yamlgraph          # ← New action type
        params:
          graph: analysis.yaml
          variables:
            input: "{job_data}"
          success: done          # ← Triggers next FSM transition
          failure: analysis_failed
```

### Direction 2: YAMLGraph → FSM (trigger transitions)

```python
# YAMLGraph Python node sends event to FSM control socket
def notify_controller(state):
    import socket, json
    sock_path = "/tmp/statemachine-control-controller.sock"
    payload = {"type": "analysis_complete", "payload": state["result"]}
    
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(payload).encode(), sock_path)
    return {"notified": True}
```

### What Each Side Provides

| FSM Handles | YAMLGraph Handles |
|-------------|-------------------|
| Job queue management | LLM prompting |
| Retry logic & error recovery | Structured outputs (Pydantic) |
| Multi-machine coordination | Multi-provider LLMs |
| Audit trail (write-only events) | DAG execution |
| WebSocket monitoring UI | Checkpointing |
| SLA timers & timeouts | Human-in-the-loop interrupts |

**Key insight:** Neither project absorbs the other's complexity. The integration is at the boundary via actions and events.

---

## Comparative Analysis

### Architecture Comparison

```
┌─────────────────────────────────────────────────────────────┐
│                  statemachine-engine                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ waiting │───►│processing│───►│completed│    │  error  │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│       ▲              │                              │       │
│       └──────────────┴──────────────────────────────┘       │
│                    (event loop)                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       YAMLGraph                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │  input  │───►│  llm    │───►│ router  │───►│ output  │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│                                      │                      │
│                              ┌───────┴───────┐              │
│                              ▼               ▼              │
│                         ┌─────────┐    ┌─────────┐          │
│                         │  path_a │    │  path_b │          │
│                         └─────────┘    └─────────┘          │
│                              (DAG execution)                │
└─────────────────────────────────────────────────────────────┘
```

### Feature Matrix

| Feature | statemachine-engine | YAMLGraph |
|---------|---------------------|-----------|
| **Config format** | YAML (states, transitions) | YAML (nodes, edges) |
| **Execution model** | Event loop with polling | LangGraph StateGraph |
| **Persistence** | SQLite job queue | Memory/SQLite/Redis checkpointers |
| **Communication** | Unix sockets, WebSockets | In-process, FastAPI optional |
| **Actions/Nodes** | 14 builtin actions | 10 node types |
| **LLM support** | None (custom action needed) | Native multi-provider |
| **Human-in-loop** | Via events/UI | `type: interrupt` nodes |
| **Visualization** | Kanban + FSM diagrams | Mermaid diagrams |
| **Variable interpolation** | `{var}`, `{nested.path}` | `{var}`, Jinja2 `{{ }}` |

### Codebase Stats

| Metric | statemachine-engine | YAMLGraph |
|--------|---------------------|-----------|
| Version | v1.0.73 | v0.x |
| Python lines | ~8,200 | ~11,600 |
| Tests | 310+ (124 collected, 21 errors) | ~1,037 |
| CHANGELOG | 89KB | Smaller |
| Dependencies | PyYAML, FastAPI, websockets | LangGraph, Pydantic, LLM SDKs |

---

## Shared Philosophy

Both projects follow:

1. **YAML-first** — Declarative configuration over imperative code
2. **Pluggable actions** — Extensible via custom modules
3. **TDD discipline** — Test-driven development
4. **KISS/DRY/YAGNI** — Explicit guiding principles

### Interpolation Syntax Overlap

Both use `{variable}` syntax with slight differences:

```yaml
# statemachine-engine
command: "echo Processing job {job_id}"
payload:
  result: "{nested.path}"

# YAMLGraph
system: "You are helping with {concept}"
user: "{{ items | join(', ') }}"  # Jinja2 mode
```

---

## Integration Patterns

### Pattern 1: YAMLGraph as FSM Action

Add a `yamlgraph` action to statemachine-engine:

```yaml
# statemachine-engine config
transitions:
  - from: processing
    to: analyzed
    event: job_analyzed
    actions:
      - type: yamlgraph
        params:
          graph: "/path/to/analysis-graph.yaml"
          variables:
            document: "{job_data.content}"
          output_key: analysis_result
          success: job_analyzed
          failure: analysis_failed
```

**Implementation sketch:**

```python
# statemachine_engine/actions/builtin/yamlgraph_action.py
from statemachine_engine.actions.base import BaseAction

class YamlGraphAction(BaseAction):
    async def execute(self, context):
        from yamlgraph import load_graph, execute_graph
        
        graph_path = self.params.get('graph')
        variables = self.params.get('variables', {})
        output_key = self.params.get('output_key', 'yamlgraph_result')
        
        graph = load_graph(graph_path)
        result = await execute_graph(graph, variables)
        
        context[output_key] = result
        return self.params.get('success', 'completed')
```

### Pattern 0: Simple Custom Action (Recommended Starting Point)

**No framework changes needed.** Just create a custom action in your project:

```python
# my_project/actions/analyze_action.py
from statemachine_engine.actions.base import BaseAction

class AnalyzeAction(BaseAction):
    """Custom action that runs a YAMLGraph pipeline."""
    
    async def execute(self, context):
        # Import YAMLGraph at runtime
        from yamlgraph import load_graph
        from yamlgraph.executor import execute_graph
        
        # Run the pipeline with context data
        graph = load_graph("graphs/analysis.yaml")
        result = await execute_graph(graph, {
            "input": context.get("job_data", {})
        })
        
        # Store result in FSM context for downstream actions
        context["analysis_result"] = result
        
        # Return event to trigger FSM transition
        return "analysis_complete"
```

**Usage in FSM config:**

```yaml
# worker.yaml
transitions:
  - from: processing
    to: analyzed
    event: analysis_complete
    actions:
      - type: analyze  # Maps to AnalyzeAction via ActionLoader
```

**Why this is simpler:**
- No changes to either framework
- Standard statemachine-engine custom action pattern
- YAMLGraph is just a library call
- Works today, no waiting for integration

### Pattern 2: FSM Event Bridge from YAMLGraph

YAMLGraph Python node sends events to statemachine-engine:

```yaml
# YAMLGraph graph.yaml
nodes:
  - name: notify_fsm
    type: python
    function: nodes.send_fsm_event
    inputs:
      event_type: analysis_complete
      target_machine: controller
      payload:
        result: "{analysis}"
```

```python
# nodes.py
import socket
import json

def send_fsm_event(state):
    sock_path = f"/tmp/statemachine-control-{state['target_machine']}.sock"
    payload = {
        "type": state["event_type"],
        "payload": state.get("payload", {})
    }
    
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(payload).encode(), sock_path)
    
    return {"fsm_notified": True}
```

### Pattern 3: Shared Job Queue

statemachine-engine manages job queue, YAMLGraph processes jobs:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Job Producer   │────►│  SQLite Queue   │◄────│  FSM Controller │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  YAMLGraph Worker   │
                    │  (LLM processing)   │
                    └─────────────────────┘
```

---

## Use Case Brainstorming

### 1. Document Processing Pipeline

**Scenario:** OCR → Analysis → Human Review → Archive

```
FSM States: receiving → ocr_processing → llm_analysis → human_review → archived
YAMLGraph: OCR cleanup graph, Analysis graph, Summary graph
```

```yaml
# FSM: document-processor.yaml
transitions:
  - from: ocr_processing
    to: llm_analysis
    event: ocr_complete
    actions:
      - type: yamlgraph
        params:
          graph: graphs/ocr-cleanup.yaml
          variables:
            raw_text: "{ocr_output}"
          output_key: cleaned_text
          success: ocr_complete

  - from: llm_analysis
    to: human_review
    event: analysis_complete
    actions:
      - type: yamlgraph
        params:
          graph: graphs/document-analysis.yaml
          variables:
            document: "{cleaned_text}"
          output_key: analysis
          success: analysis_complete
```

### 2. Customer Support Automation

**Scenario:** Ticket intake → Auto-categorization → Agent routing → Resolution

```
FSM: Controls ticket lifecycle and SLA timers
YAMLGraph: Intent classification, response generation, satisfaction analysis
```

**Flow:**
1. FSM receives ticket event → spawns categorization
2. YAMLGraph classifies intent → returns category
3. FSM routes to appropriate queue based on category
4. YAMLGraph generates suggested response
5. Human agent reviews/sends
6. FSM tracks resolution metrics

### 3. CI/CD with AI Review

**Scenario:** PR submitted → Code analysis → AI review → Human approval → Deploy

```yaml
# FSM states
states:
  - pr_received
  - analyzing
  - ai_reviewed
  - awaiting_human
  - approved
  - deploying
  - deployed

# YAMLGraph handles
graphs:
  - code-analysis.yaml  # Static analysis + LLM commentary
  - review-summary.yaml # Generate PR summary
  - deploy-risk.yaml    # Assess deployment risk
```

### 4. Medical Record Processing (HIPAA-Compliant)

**Scenario:** Records arrive → Anonymization → Analysis → Report generation

```
FSM: Audit trail, compliance checkpoints, job queue
YAMLGraph: PHI detection, anonymization, clinical summarization
```

**Why this combo works:**
- FSM provides audit trail (write-only event log)
- YAMLGraph provides LLM processing
- SQLite queue ensures no records lost
- WebSocket UI for monitoring

### 5. Content Moderation Pipeline

**Scenario:** User content → Multi-stage moderation → Human escalation → Decision

```yaml
# FSM handles
- Rate limiting (states: accepting, throttled)
- Escalation routing (states: auto_approved, flagged, escalated)
- Appeals process (states: appealed, reviewed, final)

# YAMLGraph handles
- Initial content classification (safe/borderline/unsafe)
- Policy violation detection
- Appeal analysis
- Explanation generation for users
```

### 6. Multi-Agent Research System

**Scenario:** Research query → Parallel research agents → Synthesis → Report

```
FSM: Coordinates multiple YAMLGraph workers
     States: planning → researching → synthesizing → reviewing → complete
     
YAMLGraph graphs:
  - research-planner.yaml (decompose query into sub-questions)
  - web-researcher.yaml (search and summarize)
  - synthesizer.yaml (combine findings)
  - report-generator.yaml (format output)
```

**FSM spawns parallel workers:**
```yaml
- from: planning
  to: researching
  event: plan_ready
  actions:
    - type: get_pending_jobs  # Get all sub-questions
    - type: spawn_batch       # Spawn YAMLGraph workers for each
        params:
          graph: graphs/web-researcher.yaml
```

### 7. E-commerce Order Processing

**Scenario:** Order placed → Fraud check → Inventory → Fulfillment → Delivery

```
FSM: Order state machine with retry logic
     States: received → fraud_check → inventory_check → fulfilling → shipped → delivered
     
YAMLGraph:
  - fraud-detector.yaml (LLM-based anomaly detection)
  - customer-communication.yaml (personalized updates)
  - issue-resolver.yaml (handle exceptions)
```

### 8. Educational Content Generation

**Scenario:** Topic request → Curriculum design → Content generation → Review

```yaml
# FSM manages production pipeline
states:
  - topic_received
  - curriculum_designed
  - content_generating  # Multiple YAMLGraph workers
  - content_ready
  - human_review
  - published

# YAMLGraph generates content
graphs:
  - curriculum-designer.yaml
  - lesson-generator.yaml (map node for parallel lessons)
  - quiz-generator.yaml
  - summary-generator.yaml
```

---

## Implementation Roadmap

### Phase 1: Proof of Concept (Low effort)

1. Create `yamlgraph` action for statemachine-engine
2. Create `send_fsm_event` utility for YAMLGraph
3. Build one demo (document processing)

### Phase 2: Integration Package

1. Shared interpolation utilities
2. Common logging format
3. Unified config validation

### Phase 3: Advanced Features

1. Shared checkpointing (FSM state + YAMLGraph state)
2. Combined monitoring UI
3. Cross-project tracing (LangSmith + FSM events)

---

## Technical Considerations

### Socket Communication

statemachine-engine uses Unix sockets for low-latency IPC:
- Control sockets: `/tmp/statemachine-control-{machine}.sock`
- Event socket: `/tmp/statemachine-events.sock`

YAMLGraph could:
1. Send events via control sockets (trigger transitions)
2. Listen on event socket (react to FSM state changes)

### State Synchronization

Challenge: Keeping FSM state and YAMLGraph checkpointer in sync

Options:
1. **Loose coupling** — FSM calls YAMLGraph as black box
2. **Shared DB** — Both use same SQLite for state
3. **Event sourcing** — FSM events trigger YAMLGraph, results trigger FSM events

### Error Handling

Both have error patterns:
- statemachine-engine: Wildcard transitions, retry actions
- YAMLGraph: `PipelineError.from_exception()`, error state field

Combined approach:
```yaml
# FSM catches YAMLGraph failures
- from: processing
  to: error_recovery
  event: yamlgraph_failed
  actions:
    - type: log
      message: "YAMLGraph error: {yamlgraph_error}"
    - type: send_event
      params:
        target: alerting
        event_type: pipeline_error
```

---

## Non-Goals

What this integration should **NOT** attempt:

1. **Merging the projects** — They solve different problems
2. **Replacing FSM with YAMLGraph** — FSM handles things LangGraph doesn't
3. **Adding FSM logic to YAMLGraph core** — Keep LLM focus
4. **Shared codebase** — Maintain as separate packages with optional integration

---

## Questions for Further Exploration

1. Should YAMLGraph expose an async API for FSM actions?
2. How to handle long-running YAMLGraph executions in FSM context?
3. Should FSM poll YAMLGraph status or use callbacks?
4. Can WebSocket server aggregate both FSM and YAMLGraph events?
5. Is there value in a unified CLI (`workflow run ...`)?

---

## Next Steps

- [ ] Discuss with stakeholders
- [ ] Prototype `yamlgraph` action in statemachine-engine
- [ ] Build document-processing demo
- [ ] Measure latency overhead of integration
- [ ] Document API boundaries

---

## References

- [statemachine-engine README](https://github.com/sheikkinen/statemachine-engine)
- [statemachine-engine CLAUDE.md](../statemachine-engine/CLAUDE.md)
- [YAMLGraph Architecture](../ARCHITECTURE.md)
- [YAMLGraph Getting Started](../reference/getting-started.md)
