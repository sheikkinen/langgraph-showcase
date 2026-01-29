# Feature Request: JavaScript/TypeScript API Client

**Priority:** MEDIUM
**Type:** Feature
**Status:** Proposed
**Effort:** 3-5 days
**Requested:** 2026-01-29

## Summary

Create a reusable FastAPI server and TypeScript client SDK for running YAMLGraph pipelines from JavaScript/TypeScript applications.

## Problem

Frontend and Node.js applications cannot directly use YAMLGraph (Python). Current options:
1. Shell out to Python CLI (clunky, no streaming)
2. Copy the `examples/npc/api/` pattern for each project (duplication)

Need a clean separation: Python backend runs graphs, JS frontend consumes results.

## Proposed Solution

### Phase 1: Generic API Server

Extract and generalize from `examples/npc/api/` into `yamlgraph/api/`:

```python
# yamlgraph/api/server.py
from fastapi import FastAPI
from yamlgraph.api.routes import graph_router

app = FastAPI(title="YAMLGraph API")
app.include_router(graph_router, prefix="/api/v1")
```

**Endpoints:**

```
POST /api/v1/graphs/{graph_path}/run
  Body: { "inputs": {...}, "thread_id": "optional" }
  Response: { "result": {...}, "thread_id": "...", "status": "complete|interrupted" }

POST /api/v1/graphs/{graph_path}/resume
  Body: { "thread_id": "...", "input": "user response" }
  Response: { "result": {...}, "status": "complete|interrupted" }

GET /api/v1/graphs/{graph_path}/state/{thread_id}
  Response: { "state": {...}, "next_nodes": [...] }

GET /api/v1/graphs
  Response: { "graphs": ["path1.yaml", "path2.yaml", ...] }
```

### Phase 2: TypeScript Client SDK

```typescript
// @yamlgraph/client

import { YAMLGraphClient, GraphResult } from '@yamlgraph/client';

const client = new YAMLGraphClient({ baseUrl: 'http://localhost:8000' });

// Run a graph
const result = await client.run('examples/npc/npc-creation.yaml', {
  concept: 'grumpy dwarf blacksmith'
});

// Handle interrupts (human-in-the-loop)
const encounter = await client.run('examples/npc/encounter-multi.yaml', {
  npcs: [...],
  location: 'tavern'
});

if (encounter.status === 'interrupted') {
  const resumed = await client.resume(encounter.threadId, 'The door bursts open!');
}

// Streaming (future)
for await (const event of client.stream('path/to/graph.yaml', inputs)) {
  console.log(event.node, event.output);
}
```

### Phase 3: WebSocket Support (Optional)

For real-time streaming of node outputs:

```typescript
const ws = client.connect('path/to/graph.yaml', inputs);
ws.on('node:complete', (node, output) => { ... });
ws.on('interrupt', (message) => { ws.resume(userInput); });
ws.on('complete', (result) => { ... });
```

## Directory Structure

```
yamlgraph/
  api/
    __init__.py
    server.py          # FastAPI app factory
    routes/
      __init__.py
      graphs.py        # Graph run/resume endpoints
      health.py        # Health check
    middleware/
      cors.py
      auth.py          # Optional API key auth

packages/
  client-js/           # TypeScript SDK (separate npm package)
    src/
      index.ts
      client.ts
      types.ts
    package.json
    tsconfig.json
```

## Acceptance Criteria

- [ ] `yamlgraph.api.server` module with FastAPI app
- [ ] `/api/v1/graphs/{path}/run` endpoint works
- [ ] `/api/v1/graphs/{path}/resume` endpoint handles interrupts
- [ ] TypeScript client published to npm as `@yamlgraph/client`
- [ ] Client handles async/await and interrupts cleanly
- [ ] Example: React app using client to run NPC creation
- [ ] Tests for API endpoints
- [ ] OpenAPI schema auto-generated
- [ ] Documentation with usage examples

## Alternatives Considered

### Full Port to JS ❌
- Very high effort (months)
- LangGraph.js has different APIs
- Duplicate maintenance burden
- Pydantic → Zod migration pain

### YAML Schema as Contract (Future)
- Define JSON Schema for graph YAML format
- Multiple runtimes interpret same YAML
- Higher effort but enables true polyglot
- Consider for v2 if demand exists

### Pyodide/WASM ❌
- Too heavy (~40MB runtime)
- Complexity for little benefit
- Async/threading issues

## Implementation Notes

1. **Checkpointer**: Use Redis for production (multi-instance), MemorySaver for dev
2. **CORS**: Configurable origins for frontend integration
3. **Auth**: Optional API key middleware for production
4. **Graph Discovery**: Scan configured directories for `.yaml` files
5. **Error Handling**: Structured error responses with trace IDs

## Related

- [examples/npc/api/](../examples/npc/api/) - Existing pattern to generalize
- [examples/fastapi_interview.py](../examples/fastapi_interview.py) - Simple FastAPI example
- LangServe - LangChain's API approach (reference, not dependency)
