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
