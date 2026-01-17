"""Graph builders for yamlgraph pipelines.

Provides functions to build pipeline graphs from YAML configuration.

Pipeline Architecture
=====================

The main pipeline follows this flow:

```mermaid
graph LR
    A[generate] -->|content| B{should_continue}
    B -->|continue| C[analyze]
    B -->|end| E[END]
    C -->|analysis| D[summarize]
    D --> E[END]
```

State Flow:
- generate: Creates structured content from topic
- analyze: Produces analysis from generated content
- summarize: Combines all outputs into final_summary

Graph Definition:
- Pipelines are defined in graphs/*.yaml
- Loaded and compiled via graph_loader module
"""

from pathlib import Path
from typing import Any

from langgraph.graph import StateGraph

from yamlgraph.config import DEFAULT_GRAPH
from yamlgraph.graph_loader import load_and_compile
from yamlgraph.models import create_initial_state

# Type alias for dynamic state
GraphState = dict[str, Any]


def build_graph(
    graph_path: Path | str | None = None,
    checkpointer: Any | None = None,
) -> StateGraph:
    """Build a pipeline graph from YAML with optional checkpointer.

    Args:
        graph_path: Path to YAML graph definition.
                   Defaults to graphs/yamlgraph.yaml
        checkpointer: Optional LangGraph checkpointer for state persistence.
                     Use get_checkpointer() from storage.checkpointer.

    Returns:
        StateGraph ready for compilation
    """
    path = Path(graph_path) if graph_path else DEFAULT_GRAPH
    graph = load_and_compile(path)

    # Checkpointer is applied at compile time
    if checkpointer is not None:
        # Store reference for compile() to use
        graph._checkpointer = checkpointer

    return graph


def build_resume_graph() -> StateGraph:
    """Build a graph for resuming an interrupted pipeline.

    This is an alias for build_graph(). Resume works automatically
    because nodes skip execution if their output already exists in state
    (skip_if_exists behavior).

    To resume:
    1. Load saved state from database
    2. Invoke graph with that state
    3. Nodes with existing outputs are skipped

    Returns:
        StateGraph for resume (same as main pipeline)
    """
    return build_graph()


def run_pipeline(
    topic: str,
    style: str = "informative",
    word_count: int = 300,
    graph_path: Path | str | None = None,
) -> GraphState:
    """Run the complete pipeline with given inputs.

    Args:
        topic: Topic to generate content about
        style: Writing style
        word_count: Target word count
        graph_path: Optional path to graph YAML

    Returns:
        Final state with all outputs
    """
    graph = build_graph(graph_path).compile()
    initial_state = create_initial_state(
        topic=topic,
        style=style,
        word_count=word_count,
    )

    return graph.invoke(initial_state)
