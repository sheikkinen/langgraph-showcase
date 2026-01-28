# YamlGraph

[![PyPI version](https://badge.fury.io/py/yamlgraph.svg)](https://pypi.org/project/yamlgraph/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A YAML-first framework for building LLM pipelines using:

- **YAML Graph Configuration** - Declarative pipeline definition with schema validation
- **YAML Prompts** - Declarative prompt templates with Jinja2 support
- **Pydantic Models** - Structured LLM outputs
- **Multi-Provider LLMs** - Support for Anthropic, Mistral, and OpenAI
- **LangGraph** - Pipeline orchestration with resume support
- **Human-in-the-Loop** - Interrupt nodes for user input
- **Streaming** - Token-by-token LLM output
- **Async Support** - FastAPI-ready async execution
- **Checkpointers** - Memory, SQLite, and Redis state persistence
- **Graph-Relative Prompts** - Colocate prompts with graphs
- **JSON Extraction** - Auto-extract JSON from LLM responses
- **LangSmith** - Observability and tracing
- **JSON Export** - Result serialization

## What is YAMLGraph?

**YAMLGraph** is a declarative LLM pipeline orchestration framework that lets you define complex AI workflows entirely in YAML—no Python required for 60-80% of use cases. Built on LangGraph, it provides multi-provider LLM support (Anthropic, OpenAI, Mistral, Replicate), parallel batch processing via map nodes (using LangGraph Send), LLM-driven conditional routing, and human-in-the-loop interrupts with checkpointing. Pipelines are version-controlled, linted, and observable via LangSmith. The key insight: by constraining the API surface to YAML + Jinja2 templates + Pydantic schemas, YAMLGraph trades some flexibility for dramatically faster prototyping, easier maintenance, and built-in best practices—making it ideal for teams who want production-ready AI pipelines without the complexity of full-code frameworks.

## Installation

### From PyPI

```bash
pip install yamlgraph

# With Redis support for distributed checkpointing
pip install yamlgraph[redis]
```

### From Source

```bash
git clone https://github.com/sheikkinen/yamlgraph.git
cd yamlgraph
pip install -e ".[dev]"
```

## Quick Start

### 1. Create a Prompt

Create `prompts/greet.yaml`:

```yaml
system: |
  You are a friendly assistant.

user: |
  Say hello to {name} in a {style} way.
```

### 2. Create a Graph

Create `graphs/hello.yaml`:

```yaml
version: "1.0"
name: hello-world

nodes:
  greet:
    type: llm
    prompt: greet
    variables:
      name: "{state.name}"
      style: "{state.style}"
    state_key: greeting

edges:
  - from: START
    to: greet
  - from: greet
    to: END
```

### 3. Set API Key

```bash
export ANTHROPIC_API_KEY=your-key-here
# Or: export MISTRAL_API_KEY=... or OPENAI_API_KEY=...
```

### 4. Run It

```bash
yamlgraph graph run graphs/hello.yaml --var name="World" --var style="enthusiastic"
```

Or use the Python API:

```python
from yamlgraph.graph_loader import load_and_compile

graph = load_and_compile("graphs/hello.yaml")
app = graph.compile()
result = app.invoke({"name": "World", "style": "enthusiastic"})
print(result["greeting"])
```

---

## More Examples

```bash
# Content generation pipeline
yamlgraph graph run graphs/yamlgraph.yaml --var topic="AI" --var style=casual

# Sentiment-based routing
yamlgraph graph run graphs/router-demo.yaml --var message="I love this!"

# Self-correction loop (Reflexion pattern)
yamlgraph graph run graphs/reflexion-demo.yaml --var topic="climate change"

# AI agent with shell tools
yamlgraph graph run graphs/git-report.yaml --var input="What changed recently?"

# Web research agent (requires: pip install yamlgraph[websearch])
yamlgraph graph run graphs/web-research.yaml --var topic="LangGraph tutorials"

# Code quality analysis with shell tools
yamlgraph graph run graphs/code-analysis.yaml --var path="yamlgraph" --var package="yamlgraph"

# Implementation agent - analyze code and generate plans
yamlgraph graph run examples/codegen/impl-agent.yaml \
  --var 'story=Add timeout to websearch' --var scope=yamlgraph/tools

# Meta: YAMLGraph brainstorms its own features
yamlgraph graph run graphs/feature-brainstorm.yaml --var focus="tools"

# Parallel fan-out with map nodes
yamlgraph graph run examples/storyboard/animated-character-graph.yaml \
  --var concept="A brave mouse knight" --var model=hidream
```

### Human-in-the-Loop (Interrupt Nodes)

Create interactive workflows that pause for user input:

```yaml
# graphs/interview.yaml
checkpointer:
  type: memory

nodes:
  ask_name:
    type: interrupt
    message: "What is your name?"
    resume_key: user_name

  greet:
    type: llm
    prompt: greet
    variables:
      name: "{state.user_name}"
```

```python
from langgraph.types import Command
from yamlgraph.executor_async import load_and_compile_async, run_graph_async

app = await load_and_compile_async("graphs/interview.yaml")
config = {"configurable": {"thread_id": "session-1"}}

result = await run_graph_async(app, {}, config)
# result["__interrupt__"] contains the question

result = await run_graph_async(app, Command(resume="Alice"), config)
# result["greeting"] contains personalized response
```

### Streaming

Token-by-token LLM output for real-time UX:

```python
from yamlgraph.executor_async import execute_prompt_streaming

async for token in execute_prompt_streaming("greet", {"name": "World"}):
    print(token, end="", flush=True)
```

Or in YAML nodes:

```yaml
nodes:
  generate:
    type: llm
    prompt: story
    stream: true
```

### Graph-Relative Prompts

Colocate prompts with graphs for cleaner project structures:

```yaml
# questionnaires/audit/graph.yaml
defaults:
  prompts_relative: true  # Resolve prompts from graph directory

nodes:
  opening:
    type: llm
    prompt: prompts/opening  # → questionnaires/audit/prompts/opening.yaml
```

### JSON Extraction

Auto-extract JSON from LLM responses wrapped in markdown:

```yaml
nodes:
  extract:
    type: llm
    prompt: extract_fields
    state_key: data
    parse_json: true  # {"key": "value"} instead of "```json..."
```

### CLI Utilities

```bash
yamlgraph graph list                         # List available graphs
yamlgraph graph info graphs/router-demo.yaml # Show graph structure
yamlgraph graph validate graphs/*.yaml       # Validate graph schemas
yamlgraph graph lint graphs/*.yaml           # Lint graphs for common issues
yamlgraph graph codegen graphs/my-graph.yaml # Generate TypedDict for IDE support
yamlgraph list-runs                          # View recent runs
yamlgraph resume --thread-id abc123          # Resume a run
yamlgraph export --thread-id abc123          # Export run to JSON

# Observability (requires LangSmith)
yamlgraph trace --verbose                    # View execution trace
yamlgraph mermaid                            # Show pipeline as Mermaid diagram
```

### IDE Type Support

Generate TypedDict code from your graph for IDE autocomplete and type checking:

```bash
# Generate to stdout
yamlgraph graph codegen graphs/interview-demo.yaml

# Write to file
yamlgraph graph codegen graphs/interview-demo.yaml -o interview_state.py

# Include base fields (thread_id, errors, etc.)
yamlgraph graph codegen graphs/interview-demo.yaml --include-base
```

Use the generated types in your Python code:

```python
from interview_state import InterviewDemoState

def process_result(state: InterviewDemoState) -> None:
    print(state["questions"])  # IDE autocomplete works!
```

## Documentation

📚 **Start here:** [reference/README.md](reference/README.md) - Complete index of all 18 reference docs

### Reading Order

| Level | Document | Description |
|-------|----------|-------------|
| 🟢 Beginner | [Quick Start](reference/quickstart.md) | Create your first pipeline in 5 minutes |
| 🟢 Beginner | [Graph YAML](reference/graph-yaml.md) | Node types, edges, tools, state |
| 🟢 Beginner | [Prompt YAML](reference/prompt-yaml.md) | Schema and template syntax |
| 🟡 Intermediate | [Common Patterns](reference/patterns.md) | Router, loops, agents |
| 🟡 Intermediate | [Map Nodes](reference/map-nodes.md) | Parallel fan-out processing |
| 🟡 Intermediate | [Interrupt Nodes](reference/interrupt-nodes.md) | Human-in-the-loop |
| 🔴 Advanced | [Subgraph Nodes](reference/subgraph-nodes.md) | Modular graph composition |
| 🔴 Advanced | [Async Usage](reference/async-usage.md) | FastAPI integration |
| 🔴 Advanced | [Checkpointers](reference/checkpointers.md) | State persistence |

## Architecture

🏗️ **For core developers:** See [ARCHITECTURE.md](ARCHITECTURE.md) for internal design, extension points, and contribution guidelines.

### Data Flow

```mermaid
flowchart TB
    subgraph Input["📥 Input Layer"]
        CLI["CLI Command"]
        YAML_G["graphs/*.yaml"]
        YAML_P["prompts/*.yaml"]
    end

    subgraph Core["⚙️ Core Processing"]
        GL["graph_loader.py<br/>YAML → StateGraph"]
        NF["node_factory.py<br/>Create Node Functions"]
        EH["error_handlers.py<br/>Skip/Retry/Fail/Fallback"]
        EX["executor.py<br/>Prompt Execution"]
    end

    subgraph LLM["🤖 LLM Layer"]
        LF["llm_factory.py"]
        ANT["Anthropic"]
        MIS["Mistral"]
        OAI["OpenAI"]
    end

    subgraph State["💾 State Layer"]
        SB["state_builder.py<br/>Dynamic TypedDict"]
        CP["checkpointer.py<br/>SQLite Persistence"]
        DB[(SQLite DB)]
    end

    subgraph Output["📤 Output Layer"]
        EXP["export.py"]
        JSON["JSON Export"]
        LS["LangSmith Traces"]
    end

    CLI --> GL
    YAML_G --> GL
    YAML_P --> EX
    GL --> NF
    NF --> EH
    EH --> EX
    EX --> LF
    LF --> ANT & MIS & OAI
    GL --> SB
    SB --> CP
    CP --> DB
    EX --> EXP
    EXP --> JSON
    EX --> LS
```

### Directory Structure

```
yamlgraph/
├── README.md
├── pyproject.toml        # Package definition with CLI entry point and dependencies
├── .env.sample           # Environment template
│
├── graphs/               # YAML graph definitions
│   ├── yamlgraph.yaml    # Main pipeline definition
│   ├── router-demo.yaml  # Tone-based routing demo
│   ├── reflexion-demo.yaml # Self-refinement loop demo
│   └── git-report.yaml   # AI agent demo with shell tools
│
├── yamlgraph/            # Main package
│   ├── __init__.py       # Package exports
│   ├── builder.py        # Graph builders (loads from YAML)
│   ├── graph_loader.py   # YAML → LangGraph compiler
│   ├── config.py         # Centralized configuration
│   ├── executor.py       # YAML prompt executor
│   ├── cli.py            # CLI commands
│   │
│   ├── models/           # Pydantic models
│   │   ├── __init__.py
│   │   ├── schemas.py    # Framework schemas (ErrorType, PipelineError, GenericReport)
│   │   ├── state_builder.py  # Dynamic state generation from YAML
│   │   └── graph_schema.py   # Pydantic schema validation
│   │
│   ├── tools/            # Tool execution
│   │   ├── __init__.py
│   │   ├── shell.py      # Shell command executor
│   │   ├── nodes.py      # Tool node factory
│   │   └── agent.py      # Agent node factory
│   │
│   ├── storage/          # Persistence layer
│   │   ├── __init__.py
│   │   ├── database.py   # SQLite wrapper
│   │   └── export.py     # JSON export
│   │
│   └── utils/            # Utilities
│       ├── __init__.py
│       ├── llm_factory.py # Multi-provider LLM creation
│       └── langsmith.py  # Tracing helpers
│
├── prompts/              # YAML prompt templates
│   ├── greet.yaml
│   ├── analyze.yaml
│   ├── analyze_list.yaml # Jinja2 example with loops/filters
│   ├── generate.yaml
│   ├── summarize.yaml
│   └── router-demo/      # Tone routing prompts
│       ├── classify_tone.yaml
│       ├── respond_positive.yaml
│       ├── respond_negative.yaml
│       └── respond_neutral.yaml
│
├── reference/            # YAML configuration reference docs
│   ├── README.md         # Overview and key concepts
│   ├── quickstart.md     # 5-minute getting started guide
│   ├── graph-yaml.md     # Graph YAML reference
│   ├── prompt-yaml.md    # Prompt YAML reference
│   └── patterns.md       # Common patterns and examples
│
├── tests/                # Test suite
│   ├── conftest.py       # Shared fixtures
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
│
└── outputs/              # Generated files (gitignored)
```
```

## Pipeline Flow

```mermaid
graph TD
    A["📝 generate"] -->|content| B{should_continue}
    B -->|"✓ content exists"| C["🔍 analyze"]
    B -->|"✗ error/empty"| F["🛑 END"]
    C -->|analysis| D["📊 summarize"]
    D -->|final_summary| F

    style A fill:#e1f5fe
    style C fill:#fff3e0
    style D fill:#e8f5e9
    style F fill:#fce4ec
```

### Node Outputs

| Node | Output Type | Description |
|------|-------------|-------------|
| `generate` | Inline schema | Title, content, word_count, tags |
| `analyze` | Inline schema | Summary, key_points, sentiment, confidence |
| `summarize` | `str` | Final combined summary |

Output schemas are defined inline in YAML prompt files using the `schema:` block.

### Resume Flow

Pipelines can be resumed from any checkpoint. The resume behavior uses `skip_if_exists`:
nodes check if their output already exists in state and skip LLM calls if so.

```mermaid
graph LR
    subgraph "Resume after 'analyze' completed"
        A1["Load State"] --> B1["analyze (skipped)"] --> C1["summarize"] --> D1["END"]
    end
```

```bash
# Resume an interrupted run
yamlgraph resume --thread-id abc123
```

When resumed:
- Nodes with existing outputs are **skipped** (no duplicate LLM calls)
- Only nodes without outputs in state actually run
- State is preserved via SQLite checkpointing

## Key Patterns

### 1. YAML Prompt Templates

**Simple Templating (Basic Substitution)**:
```yaml
# prompts/generate.yaml
system: |
  You are a creative content writer...

user: |
  Write about: {topic}
  Target length: approximately {word_count} words
```

**Advanced Templating (Jinja2)**:
```yaml
# prompts/analyze_list.yaml
template: |
  Analyze the following {{ items|length }} items:

  {% for item in items %}
  ### {{ loop.index }}. {{ item.title }}
  Topic: {{ item.topic }}
  {% if item.tags %}
  Tags: {{ item.tags | join(", ") }}
  {% endif %}
  {% endfor %}
```

**Template Features**:
- **Auto-detection**: Uses Jinja2 if `{{` or `{%` present, otherwise simple formatting
- **Loops**: `{% for item in items %}...{% endfor %}`
- **Conditionals**: `{% if condition %}...{% endif %}`
- **Filters**: `{{ text[:50] }}`, `{{ items | join(", ") }}`, `{{ name | upper }}`
- **Backward compatible**: Existing `{variable}` prompts work unchanged

### 2. Structured Executor

```python
from yamlgraph.executor import execute_prompt
from yamlgraph.models import GenericReport

result = execute_prompt(
    "generate",
    variables={"topic": "AI", "word_count": 300},
    output_model=GenericReport,
)
print(result.title)  # Typed access!
```

### 3. Multi-Provider LLM Support

```python
from yamlgraph.executor import execute_prompt

# Use default provider (Anthropic)
result = execute_prompt(
    "greet",
    variables={"name": "Alice", "style": "formal"},
)

# Switch to Mistral
result = execute_prompt(
    "greet",
    variables={"name": "Bob", "style": "casual"},
    provider="mistral",
)

# Or set via environment variable
# PROVIDER=openai yamlgraph graph run ...
```

Supported providers:
- **Anthropic** (default): Claude models
- **Mistral**: Mistral Large and other models
- **OpenAI**: GPT-4 and other models

Provider selection priority:
1. Function parameter: `execute_prompt(..., provider="mistral")`
2. YAML metadata: `provider: mistral` in prompt file
3. Environment variable: `PROVIDER=mistral`
4. Default: `anthropic`

### 4. YAML Graph Configuration

Pipelines are defined declaratively in YAML and compiled to LangGraph:

```yaml
# graphs/yamlgraph.yaml
version: "1.0"
name: yamlgraph-demo
description: Content generation pipeline

defaults:
  provider: mistral
  temperature: 0.7

nodes:
  generate:
    type: llm
    prompt: generate
    output_schema:  # Inline schema - no Python model needed!
      title: str
      content: str
      word_count: int
      tags: list[str]
    temperature: 0.8
    variables:
      topic: "{state.topic}"
      word_count: "{state.word_count}"
      style: "{state.style}"
    state_key: generated

  analyze:
    type: llm
    prompt: analyze
    output_schema:  # Inline schema
      summary: str
      key_points: list[str]
      sentiment: str
      confidence: float
    temperature: 0.3
    variables:
      content: "{state.generated.content}"
    state_key: analysis
    requires: [generated]

  summarize:
    type: llm
    prompt: summarize
    temperature: 0.5
    state_key: final_summary
    requires: [generated, analysis]

edges:
  - from: START
    to: generate
  - from: generate
    to: analyze
    condition: continue
  - from: generate
    to: END
    condition: end
  - from: analyze
    to: summarize
  - from: summarize
    to: END
```

**Load and run**:
```python
from yamlgraph.builder import build_graph

graph = build_graph().compile()  # Loads from graphs/yamlgraph.yaml
result = graph.invoke(initial_state)
```

### 5. State Persistence

```python
from yamlgraph.storage import YamlGraphDB

db = YamlGraphDB()
db.save_state("thread-123", state)
state = db.load_state("thread-123")
```

### 6. LangSmith Tracing

```python
from yamlgraph.utils.langsmith import print_run_tree

print_run_tree(verbose=True)
# 📊 Execution Tree:
# └─ yamlgraph_pipeline (12.3s) ✅
#    ├─ generate (5.2s) ✅
#    ├─ analyze (3.1s) ✅
#    └─ summarize (4.0s) ✅
```

#### Self-Correcting Pipelines

Use LangSmith tools to let agents inspect previous runs and fix errors:

```python
from yamlgraph.utils.langsmith import get_run_details, get_run_errors, get_failed_runs

# Get details of the last run
details = get_run_details()  # or get_run_details("specific-run-id")
print(details["status"])  # "success" or "error"

# Get all errors from a run and its child nodes
errors = get_run_errors()
for e in errors:
    print(f"{e['node']}: {e['error']}")

# List recent failed runs
failures = get_failed_runs(limit=5)
```

As agent tools (see [reference/langsmith-tools.md](reference/langsmith-tools.md)):

```yaml
tools:
  check_last_run:
    type: python
    module: yamlgraph.tools.langsmith_tools
    function: get_run_details_tool
    description: "Get status and errors from the last pipeline run"

  get_errors:
    type: python
    module: yamlgraph.tools.langsmith_tools
    function: get_run_errors_tool
    description: "Get detailed error info from a run"

nodes:
  self_correct:
    type: agent
    prompt: error_analyzer
    tools: [check_last_run, get_errors]
    max_iterations: 3
```

### 7. Shell Tools & Agent Nodes

Define shell tools and let the LLM decide when to use them:

```yaml
# graphs/git-report.yaml
tools:
  recent_commits:
    type: shell
    command: git log --oneline -n {count}
    description: "List recent commits"

  changed_files:
    type: shell
    command: git diff --name-only HEAD~{n}
    description: "List files changed in last n commits"

nodes:
  analyze:
    type: agent              # LLM decides which tools to call
    prompt: git_analyst
    tools: [recent_commits, changed_files]
    max_iterations: 8
    state_key: analysis
```

Run the git analysis agent:

```bash
yamlgraph git-report -q "What changed recently?"
yamlgraph git-report -q "Summarize the test directory"
```

### 8. Web Search Tools

Enable agents to search the web using DuckDuckGo (no API key required):

```bash
pip install yamlgraph[websearch]
```

```yaml
# graphs/web-research.yaml
tools:
  search_web:
    type: websearch
    provider: duckduckgo
    max_results: 5
    description: "Search the web for current information"

nodes:
  research:
    type: agent
    prompt: web-research/researcher
    tools: [search_web]
    max_iterations: 5
    state_key: research
```

Run web research:

```bash
yamlgraph graph run graphs/web-research.yaml --var topic="LangGraph tutorials"
```

### 9. Code Quality Analysis

Run automated code analysis with shell-based quality tools:

```yaml
# graphs/code-analysis.yaml
state:
  path: str      # Directory to analyze
  package: str   # Package name for coverage

tools:
  run_ruff:
    type: shell
    command: ruff check {path} --output-format=text 2>&1
    description: "Run ruff linter for code style issues"

  run_tests:
    type: shell
    command: python -m pytest {path} -q --tb=no 2>&1 | tail -10
    description: "Run pytest"

  run_bandit:
    type: shell
    command: bandit -r {path} -ll -q 2>&1
    description: "Security vulnerability scanner"

nodes:
  run_analysis:
    type: agent
    prompt: code-analysis/analyzer
    tools: [run_ruff, run_tests, run_coverage, run_bandit, run_radon, run_vulture]
    max_iterations: 12
    state_key: analysis_results

  generate_recommendations:
    type: llm
    prompt: code-analysis/recommend
    requires: [analysis_results]
    state_key: recommendations
```

Run code analysis (yamlgraph analyzes itself!):

```bash
yamlgraph graph run graphs/code-analysis.yaml --var path="yamlgraph" --var package="yamlgraph"
```

**Tool types:**
- `type: shell` - Execute shell commands with variable substitution
- `type: websearch` - Web search via DuckDuckGo (provider: duckduckgo)
- `type: python` - Execute custom Python functions

**Node types:**
- `type: llm` - Standard LLM call with structured output
- `type: router` - Classify and route to different paths
- `type: map` - Parallel fan-out over lists with `Send()`
- `type: python` - Execute custom Python functions
- `type: agent` - LLM loop that autonomously calls tools

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key (* if using Anthropic) |
| `MISTRAL_API_KEY` | No | Mistral API key (required if using Mistral) |
| `OPENAI_API_KEY` | No | OpenAI API key (required if using OpenAI) |
| `PROVIDER` | No | Default LLM provider (anthropic/mistral/openai) |
| `ANTHROPIC_MODEL` | No | Anthropic model (default: claude-sonnet-4-20250514) |
| `MISTRAL_MODEL` | No | Mistral model (default: mistral-large-latest) |
| `OPENAI_MODEL` | No | OpenAI model (default: gpt-4o) |
| `LANGCHAIN_TRACING` | No | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | LangSmith API key |
| `LANGCHAIN_ENDPOINT` | No | LangSmith endpoint URL |
| `LANGCHAIN_PROJECT` | No | LangSmith project name |

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run with coverage report
pytest tests/ --cov=yamlgraph --cov-report=term-missing

# Run with HTML coverage report
pytest tests/ --cov=yamlgraph --cov-report=html
# Then open htmlcov/index.html
```

**Current coverage**: 92% overall, 90% on graph_loader, 100% on builder/llm_factory.

## Extending the Pipeline

### Adding a New Node (YAML-First Approach)

Let's add a "fact_check" node that verifies generated content:

**Step 1: Define the output schema** (`yamlgraph/models/schemas.py`):
```python
class FactCheck(BaseModel):
    """Structured fact-checking output."""

    claims: list[str] = Field(description="Claims identified in content")
    verified: bool = Field(description="Whether claims are verifiable")
    confidence: float = Field(ge=0.0, le=1.0, description="Verification confidence")
    notes: str = Field(description="Additional context")
```

**Step 2: Create the prompt** (`prompts/fact_check.yaml`):
```yaml
system: |
  You are a fact-checker. Analyze the given content and identify
  claims that can be verified. Assess the overall verifiability.

user: |
  Content to fact-check:
  {content}

  Identify key claims and assess their verifiability.
```

**Step 3: State is auto-generated**

State fields are now generated automatically from your YAML graph config.
The `state_key` in your node config determines where output is stored:
```yaml
# Node output stored in state.fact_check automatically
fact_check:
  type: llm
  prompt: fact_check
  state_key: fact_check  # This creates the state field
```

**Step 4: Add the node to your graph** (`graphs/yamlgraph.yaml`):
```yaml
nodes:
  generate:
    type: prompt
    prompt: generate
    output_schema:  # Inline schema - no Python model needed!
      title: str
      content: str
    variables:
      topic: topic
    state_key: generated

  fact_check:  # ✨ New node - just YAML!
    type: prompt
    prompt: fact_check
    output_schema:  # Define schema inline
      is_accurate: bool
      issues: list[str]
    requires: [generated]
    variables:
      content: generated.content
    state_key: fact_check

  analyze:
    # ... existing config ...

edges:
  - from: START
    to: generate
  - from: generate
    to: fact_check
    condition:
      type: has_value
      field: generated
  - from: fact_check
    to: analyze
  # ... rest of edges ...
```

That's it! No Python node code needed. The graph loader dynamically generates the node function.

Resulting pipeline:
```mermaid
graph TD
    A[generate] --> B{has generated?}
    B -->|yes| C[fact_check]
    C --> D[analyze]
    D --> E[summarize]
    E --> F[END]
    B -->|no| F
```

### Adding Conditional Branching

Route to different nodes based on analysis results (all in YAML):

```yaml
edges:
  - from: analyze
    to: rewrite_node
    condition:
      type: field_equals
      field: analysis.sentiment
      value: negative

  - from: analyze
    to: enhance_node
    condition:
      type: field_equals
      field: analysis.sentiment
      value: positive

  - from: analyze
    to: summarize  # Default fallback
```

### Add a New Prompt

1. Create `prompts/new_prompt.yaml`:
```yaml
system: Your system prompt...
user: Your user prompt with {variables}...
```

2. Call it:
```python
result = execute_prompt("new_prompt", variables={"var": "value"})
```

### Add Structured Output

1. Define model in `yamlgraph/models/schemas.py`:
```python
class MyOutput(BaseModel):
    field: str = Field(description="...")
```

2. Use with executor:
```python
result = execute_prompt("prompt", output_model=MyOutput)
```

## Known Issues & Future Improvements

This project demonstrates solid production patterns with declarative YAML-based configuration.

### Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| YAML Graph Configuration | ✅ | Declarative pipeline definition in `graphs/yamlgraph.yaml` |
| Jinja2 Templating | ✅ | Hybrid auto-detection (simple {var} + advanced Jinja2) |
| Multi-Provider LLMs | ✅ | Factory pattern supporting Anthropic/Mistral/OpenAI |
| Dynamic Node Generation | ✅ | Nodes compiled from YAML at runtime |

### Implemented Patterns

| Feature | Status | Notes |
|---------|--------|-------|
| Branching/Routing | ✅ | `type: router` for LLM-based conditional routing |
| Self-Correction Loops | ✅ | Reflexion pattern with critique → refine cycles |
| Tool/Agent Patterns | ✅ | Shell tools + agent nodes with LangChain tool binding |
| Per-Node Error Handling | ✅ | `on_error: skip/retry/fail/fallback` |
| Conversation Memory | ✅ | Message accumulation via `AgentState.messages` |
| Native Checkpointing | ✅ | `SqliteSaver` from `langgraph-checkpoint-sqlite` |
| State Export | ✅ | JSON/Markdown export with `export_result()` |
| LangSmith Share Links | ✅ | Auto-generate public trace URLs after runs |

### LangGraph Features

| Feature | Status | Notes |
|---------|--------|-------|
| Fan-out/Fan-in | ✅ | `type: map` with `Send()` for item-level parallelism |
| Human-in-the-Loop | ✅ | `type: interrupt` nodes with `resume_key` |
| Streaming | ✅ | `stream: true` on nodes, `execute_prompt_streaming()` |
| Sub-graphs | ✅ | `type: subgraph` for nested graph composition |

### Potential Enhancements

#### Short-term (Quick Wins)
1. **Add `in` operator to conditions** - Support `status in ["done", "complete"]` expressions
2. **Document agent `max_iterations`** - Expose in YAML schema for agent nodes
3. **Add `--dry-run` flag** - Validate graph without execution

#### Medium-term (Feature Improvements)
4. **Async map node execution** - Use `asyncio.gather()` for parallel branches
5. **State field collision warnings** - Log when YAML fields override base fields
6. **Map node error aggregation** - Summary with success/failure counts per branch
7. **Add streaming** - `--stream` CLI flag for real-time output

#### Long-term (Architecture)
8. **Plugin system** - Custom node types via entry points
9. **Hot-reload for development** - File watcher for prompt/graph YAML changes
10. **OpenTelemetry integration** - Complement LangSmith with standard observability
11. **Sub-graphs** - Nested graph composition for complex workflows
12. **Human-in-the-loop** - `interrupt_before` / `interrupt_after` demonstration

## Security

### Shell Command Injection Protection

Shell tools (defined in `graphs/*.yaml` with `type: tool`) execute commands with variable substitution. All user-provided variable values are sanitized using `shlex.quote()` to prevent shell injection attacks.

```yaml
# In graph YAML - command template is trusted
tools:
  git_log:
    type: shell
    command: "git log --author={author} -n {count}"
```

**Security model:**
- ✅ **Command templates** (from YAML) are trusted configuration
- ✅ **Variable values** (from user input/LLM) are escaped with `shlex.quote()`
- ✅ **Complex types** (lists, dicts) are JSON-serialized then quoted
- ✅ **No `eval()`** - condition expressions parsed with regex, not evaluated

**Example protection:**
```python
# Malicious input is safely escaped
variables = {"author": "$(rm -rf /)"}
# Executed as: git log --author='$(rm -rf /)'  (quoted, harmless)
```

See [yamlgraph/tools/shell.py](yamlgraph/tools/shell.py) for implementation details.

### ⚠️ Security Considerations

**Shell tools execute real commands** on your system. While variables are sanitized:

1. **Command templates are trusted** - Only use shell tools from trusted YAML configs
2. **No sandboxing** - Commands run with your user permissions
3. **Agent autonomy** - Agent nodes may call tools unpredictably
4. **Review tool definitions** - Audit `tools:` section in graph YAML before running

For production deployments, consider:
- Running in a container with limited permissions
- Restricting available tools to read-only operations
- Implementing approval workflows for sensitive operations

## Documentation

- **[Reference Documentation](reference/)** - Complete guides for YAMLGraph features, node types, and advanced usage
- **[Analyzing YAML-Driven LangGraph Repositories](docs/Analyzing YAML-Driven LangGraph Repositories.md)** - Comprehensive technical analysis of YAMLGraph's architecture, LangGraph fundamentals, and strategic positioning in the AI orchestration landscape

For examples and tutorials, see the [examples/](examples/) directory.

## License

MIT

## Remember

Prompts in yaml templates, graphs in yaml, shared executor, pydantic, data stored in sqlite, langgraph, langsmith, venv, tdd red-green-refactor, modules < 400 lines, kiss
