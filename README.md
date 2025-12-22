# LangGraph Showcase App

A minimal, self-contained demonstration of a production-ready LLM pipeline using:

- **YAML Prompts** - Declarative prompt templates
- **Pydantic Models** - Structured LLM outputs
- **LangGraph** - Pipeline orchestration
- **SQLite** - State persistence
- **LangSmith** - Observability and tracing
- **JSON Export** - Result serialization

## Quick Start

### 1. Setup Environment

```bash
# Clone or copy the showcase directory
cd showcase

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install as editable package
pip install -e .

# Configure environment
cp .env.sample .env
# Edit .env with your ANTHROPIC_API_KEY
```

### 2. Run the Pipeline

```bash
# Using the CLI command (after pip install -e .)
showcase run --topic "machine learning" --style casual

# Or using python -m
python -m showcase.cli run --topic "machine learning" --style casual

# With export
showcase run -t "climate change" -s informative -w 500 --export

# View recent runs
showcase list-runs

# Resume a run
showcase resume --thread-id abc123

# View execution trace (requires LangSmith)
showcase trace --verbose
```

## Architecture

```
showcase/
├── README.md
├── pyproject.toml        # Package definition with CLI entry point
├── requirements.txt      # Dependencies
├── .env.sample           # Environment template
├── run.py                # Simple entry point
│
├── showcase/             # Main package
│   ├── __init__.py       # Package exports
│   ├── builder.py        # Graph builders + pipeline runner
│   ├── executor.py       # YAML prompt executor
│   ├── cli.py            # CLI commands
│   │
│   ├── models/           # Pydantic models
│   │   ├── __init__.py
│   │   ├── schemas.py    # Output schemas (Analysis, GeneratedContent, etc.)
│   │   └── state.py      # LangGraph state definition
│   │
│   ├── nodes/            # Graph node functions
│   │   ├── __init__.py
│   │   └── content.py    # generate, analyze, summarize nodes
│   │
│   ├── storage/          # Persistence layer
│   │   ├── __init__.py
│   │   ├── database.py   # SQLite wrapper
│   │   └── export.py     # JSON export
│   │
│   └── utils/            # Utilities
│       ├── __init__.py
│       └── langsmith.py  # Tracing helpers
│
├── prompts/              # YAML prompt templates
│   ├── greet.yaml
│   ├── analyze.yaml
│   ├── generate.yaml
│   └── summarize.yaml
│
└── outputs/              # Generated files (gitignored)
```

## Pipeline Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   generate  │ ──▶ │   analyze   │ ──▶ │  summarize  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
 GeneratedContent      Analysis          final_summary
   (Pydantic)         (Pydantic)           (string)
```

## Key Patterns

### 1. YAML Prompt Templates

```yaml
# prompts/generate.yaml
system: |
  You are a creative content writer...

user: |
  Write about: {topic}
  Target length: approximately {word_count} words
```

### 2. Structured Executor

```python
from showcase.executor import execute_prompt
from showcase.models import GeneratedContent

result = execute_prompt(
    "generate",
    variables={"topic": "AI", "word_count": 300},
    output_model=GeneratedContent,
)
print(result.title)  # Typed access!
```

### 3. LangGraph Pipeline

```python
from showcase.graph import build_showcase_graph

graph = build_showcase_graph().compile()
result = graph.invoke(initial_state)
```

### 4. State Persistence

```python
from showcase.storage import ShowcaseDB

db = ShowcaseDB()
db.save_state("thread-123", state)
state = db.load_state("thread-123")
```

### 5. LangSmith Tracing

```python
from showcase.langsmith_utils import print_run_tree

print_run_tree(verbose=True)
# 📊 Execution Tree:
# └─ showcase_graph (12.3s) ✅
#    ├─ generate (5.2s) ✅
#    ├─ analyze (3.1s) ✅
#    └─ summarize (4.0s) ✅
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `ANTHROPIC_MODEL` | No | Model name (default: claude-sonnet-4-20250514) |
| `LANGCHAIN_TRACING_V2` | No | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project name |

## Extending

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

1. Define model in `models.py`:
```python
class MyOutput(BaseModel):
    field: str = Field(description="...")
```

2. Use with executor:
```python
result = execute_prompt("prompt", output_model=MyOutput)
```

### Add Pipeline Node

1. Add node function in `graph.py`:
```python
def my_node(state: ShowcaseState) -> dict:
    # Process state
    return {"my_field": result}
```

2. Add to graph:
```python
graph.add_node("my_node", my_node)
graph.add_edge("previous", "my_node")
```

## License

MIT
