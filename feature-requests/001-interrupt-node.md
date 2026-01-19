# Feature Request: Interrupt Node Type

**ID:** 001  
**Priority:** P1 - Critical  
**Status:** ✅ Implemented  
**Effort:** 1 week  
**Requested:** 2026-01-19  
**Implemented:** 2026-01-19  
**Commit:** `3508b80`  
**Docs:** [reference/interrupt-nodes.md](../reference/interrupt-nodes.md)

## Summary

Add a new node type `interrupt` that pauses graph execution and returns control to the caller, enabling multi-turn conversational flows.

## Motivation

YamlGraph currently executes graphs to completion in a single invocation. This works for batch pipelines but prevents use cases like:

- Chatbots waiting for user input
- Human-in-the-loop approval workflows
- Multi-turn questionnaire interviews
- Interactive agents requiring confirmation

**Use case:** questionnaire-api needs to pause after generating a question, wait for user response via HTTP, then resume graph execution.

## Proposed Solution

### YAML Syntax

```yaml
nodes:
  ask_question:
    type: interrupt
    prompt: dialogue/generate_question    # Optional: generate message to show
    state_key: pending_question           # Where to store generated message
    resume_key: user_response             # Where resume will inject input
    timeout: 3600                         # Optional: session timeout in seconds
```

### Behavior

1. Node executes prompt (if provided)
2. Stores result in `state_key`
3. Sets `_interrupt: true` in state
4. Graph executor detects interrupt and returns control
5. Caller receives partial state + resume instructions
6. Later: caller invokes `resume(thread_id, {resume_key: value})`
7. Graph continues from node after interrupt

### API

```python
from yamlgraph import load_and_compile, run_until_interrupt, resume

# First invocation
graph = load_and_compile("graphs/conversation.yaml")
result = run_until_interrupt(graph, {"topic": "health"}, config)

if result["status"] == "interrupted":
    # Show result["state"]["pending_question"] to user
    # Wait for user input...
    
    # Resume with user's response
    result = resume(graph, result["thread_id"], {"user_response": "..."})
```

### Implementation Notes

```python
# yamlgraph/node_factory.py
def create_interrupt_node(node_name: str, node_config: dict) -> Callable:
    """Create node that signals graph interruption."""
    prompt_name = node_config.get("prompt")
    state_key = node_config.get("state_key", "interrupt_message")
    resume_key = node_config.get("resume_key", "user_input")
    
    def interrupt_fn(state: dict) -> dict:
        result = {}
        
        # Generate prompt if configured
        if prompt_name:
            message = execute_prompt(prompt_name, state)
            result[state_key] = message
        
        # Signal interrupt
        result["_interrupt"] = True
        result["_resume_key"] = resume_key
        result["_interrupt_node"] = node_name
        
        return result
    
    return interrupt_fn
```

```python
# yamlgraph/executor.py
def run_until_interrupt(graph, initial_state, config):
    """Execute graph until completion or interrupt."""
    app = graph.compile(checkpointer=config.get("checkpointer"))
    
    for event in app.stream(initial_state, config):
        if event.get("_interrupt"):
            return {
                "status": "interrupted",
                "thread_id": config["configurable"]["thread_id"],
                "state": event,
                "resume_key": event["_resume_key"],
            }
    
    return {"status": "complete", "state": event}
```

## Alternatives Considered

### 1. External loop around graph
**Rejected:** Loses graph state between invocations without checkpointing.

### 2. Callback-based interrupts
**Rejected:** Doesn't work with HTTP request/response model.

### 3. LangGraph's built-in interrupt()
**Considered:** LangGraph 0.2+ has `interrupt()` function. We should leverage this.

## Acceptance Criteria

- [ ] `type: interrupt` recognized in YAML schema
- [ ] Graph execution pauses at interrupt node
- [ ] `run_until_interrupt()` returns partial state
- [ ] `resume()` continues from checkpoint
- [ ] State persists between interrupt and resume
- [ ] Timeout handling works
- [ ] Integration test with multi-turn flow
- [ ] Documentation updated

## Related

- LangGraph interrupt pattern: https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/
- Feature #002: Redis Checkpointer (required for production use)
- questionnaire-api migration: docs/eval-yamlgraph-port.md
