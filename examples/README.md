# YAMLGraph Examples

Example applications demonstrating YAMLGraph capabilities.

## Quick Reference

| Example | Description | Key Features |
|---------|-------------|--------------|
| [beautify/](beautify/) | Graph → HTML infographic | LLM analysis, Mermaid diagrams, Tailwind CSS |
| [book_translator/](book_translator/) | Translate books & documents | Map nodes, parallel translation, glossary, checkpointing |
| [booking/](booking/) | Appointment booking assistant | Interrupt nodes, tool nodes, multi-turn conversation |
| [codegen/](codegen/) | Implementation agent | Tool nodes, code analysis, 24 Python tools |
| [rag/](rag/) | RAG pipeline | LanceDB vectorstore, document indexing, retrieval |
| [yamlgraph_gen/](yamlgraph_gen/) | Pipeline generator | Meta-generation, snippet composition, validation |
| [cost-router/](cost-router/) | Multi-provider routing | Router nodes, Granite/Mistral/Claude |
| [daily_digest/](daily_digest/) | Scheduled news digest | Fly.io deployment, background tasks, email |
| [npc/](npc/) | D&D NPC generator | Multi-graph, map nodes, parallel NPCs |
| [storyboard/](storyboard/) | Visual story generator | Replicate API, image generation |
| [fastapi_interview.py](fastapi_interview.py) | FastAPI integration | Async execution, interrupt handling, sessions |

## Running Examples

Most examples can be run with the CLI:

```bash
# From project root
yamlgraph graph run examples/<name>/graph.yaml --full
```

Or with specific variables:

```bash
yamlgraph graph run examples/npc/npc-creation.yaml \
  -v 'concept=grumpy dwarf blacksmith' --full
```

## By Feature

### Map Nodes (Parallel Processing)
- **book_translator/** - Parallel chapter translation and proofreading
- **npc/** - Multiple NPC encounters processed simultaneously

### Router Nodes
- **cost-router/** - Route to different LLM providers by query complexity

### Tool Nodes
- **codegen/** - 24 code analysis tools (AST, grep, jedi)
- **yamlgraph_gen/** - Meta-generation with validation tools

### Interrupt Nodes (Human-in-the-Loop)
- **fastapi_interview.py** - Web-based multi-turn conversations

### RAG (Retrieval-Augmented Generation)
- **rag/** - LanceDB vectorstore with document chunking

### External APIs
- **storyboard/** - Replicate image generation
- **daily_digest/** - Resend email, Hacker News API

### Deployment
- **daily_digest/** - Fly.io Docker deployment with GitHub Actions

## Shared Utilities

The `shared/` directory contains reusable tools:

- `replicate_tool.py` - Unified Replicate API wrapper for image generation

## Prerequisites

Each example has its own requirements. Common patterns:

```bash
# Core yamlgraph
pip install -e .

# With Replicate support (storyboard, cost-router)
pip install -e ".[replicate]"

# With RAG support (rag)
pip install -e ".[rag]"

# With digest extras (daily_digest)
pip install -e ".[digest]"
```

See individual example READMEs for specific setup instructions.
