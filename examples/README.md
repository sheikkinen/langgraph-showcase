# YAMLGraph Examples

Example applications demonstrating YAMLGraph capabilities.

## 🎓 Learning Path

Start here and progress through the demos in order:

| Step | Demo | Concept | Time |
|------|------|---------|------|
| 1 | [demos/hello](demos/hello/) | Basic LLM node, variables | 5 min |
| 2 | [demos/router](demos/router/) | Conditional routing | 10 min |
| 3 | [demos/map](demos/map/) | Parallel fan-out | 15 min |
| 4 | [demos/reflexion](demos/reflexion/) | Self-correction loops | 15 min |
| 5 | [demos/git-report](demos/git-report/) | Tool-using agents | 15 min |
| 6 | [demos/interview](demos/interview/) | Human-in-the-loop | 15 min |
| 7 | [demos/subgraph](demos/subgraph/) | Graph composition | 20 min |

After the learning path, explore production examples below.

## Quick Reference

| Example | Description | Key Features |
|---------|-------------|--------------|
| [beautify/](beautify/) | Graph → HTML infographic | LLM analysis, Mermaid diagrams, Tailwind CSS |
| [book_translator/](book_translator/) | Translate books & documents | Map nodes, parallel translation, glossary, checkpointing |
| [booking/](booking/) | Appointment booking assistant | Interrupt nodes, tool nodes, multi-turn conversation |
| [codegen/](codegen/) | Implementation agent | Tool nodes, code analysis, 24 Python tools |
| [cost-router/](cost-router/) | Multi-provider routing | Router nodes, Granite/Mistral/Claude |
| [daily_digest/](daily_digest/) | Scheduled news digest | Fly.io deployment, background tasks, email |
| [fsm-router/](fsm-router/) | FSM + YAMLGraph integration | statemachine-engine, LLM routing, job orchestration |
| [npc/](npc/) | D&D NPC generator | Multi-graph, map nodes, parallel NPCs |
| [ocr_cleanup/](ocr_cleanup/) | OCR text cleanup | Map nodes, PDF extraction, parallel LLM cleanup |
| [questionnaire/](questionnaire/) | Feature request collector | Data files, interrupt loops, conditional routing |
| [rag/](rag/) | RAG pipeline | LanceDB vectorstore, document indexing, retrieval |
| [storyboard/](storyboard/) | Visual story generator | Replicate API, image generation |
| [yamlgraph_gen/](yamlgraph_gen/) | Pipeline generator | Meta-generation, snippet composition, validation |
| [fastapi_interview.py](fastapi_interview.py) | FastAPI integration | Async execution, interrupt handling, sessions |
| [demos/soul/](demos/soul/) | Agent personality pattern | Data files, persona definition |

## Demos Index

Standalone demos in [demos/](demos/):

| Demo | Node Types | Description |
|------|------------|-------------|
| [hello](demos/hello/) | `llm` | Minimal example - start here |
| [router](demos/router/) | `router` | Tone-based conditional routing |
| [map](demos/map/) | `map`, `llm` | Parallel fan-out processing |
| [reflexion](demos/reflexion/) | `llm` | Self-correction with loop limits |
| [yamlgraph](demos/yamlgraph/) | `llm` | Multi-step pipeline |
| [git-report](demos/git-report/) | `agent` | Git analysis with tools |
| [memory](demos/memory/) | `agent` | Multi-turn with memory |
| [interview](demos/interview/) | `interrupt` | Human-in-the-loop |
| [interrupt](demos/interrupt/) | `subgraph`, `interrupt` | Subgraph interrupt tests |
| [streaming](demos/streaming/) | `llm` | Token-by-token output |
| [subgraph](demos/subgraph/) | `subgraph` | Graph composition |
| [system-status](demos/system-status/) | `tool` | Shell tool execution |
| [web-research](demos/web-research/) | `agent` | Web search agent |
| [code-analysis](demos/code-analysis/) | `tool`, `llm` | Code quality tools |
| [feature-brainstorm](demos/feature-brainstorm/) | `agent` | Self-analysis |
| [data-files](demos/data-files/) | `llm` | External data loading |
| [run-analyzer](demos/run-analyzer/) | - | Analysis utilities |
| [soul](demos/soul/) | `llm`, `data_files` | Agent personality pattern |

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
- **ocr_cleanup/** - Parallel page cleanup with LLM

### Router Nodes
- **cost-router/** - Route to different LLM providers by query complexity

### Tool Nodes
- **codegen/** - 24 code analysis tools (AST, grep, jedi)
- **yamlgraph_gen/** - Meta-generation with validation tools

### Interrupt Nodes (Human-in-the-Loop)
- **questionnaire/** - Interactive data collection with probe/recap loops
- **fastapi_interview.py** - Web-based multi-turn conversations

### Data Files (External Schema Loading)
- **questionnaire/** - Schema-driven field collection
- **demos/data-files/** - Simple data_files demonstration

### Soul Pattern (Agent Personality)
- **soul/** - Give AI agents consistent personality via data_files

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
