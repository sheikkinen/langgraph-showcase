"""Web search tool for LLM agents.

This module provides web search functionality using DuckDuckGo,
allowing agents to search the internet for current information.

No API key required for DuckDuckGo. Results include title, URL, and snippet.

Example usage in graph YAML:
    tools:
      search_web:
        type: websearch
        provider: duckduckgo
        max_results: 5
        description: "Search the web for information"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Import DuckDuckGo - try new package name first, fallback to old
try:
    from ddgs import DDGS

    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS

        DUCKDUCKGO_AVAILABLE = True
    except ImportError:
        DDGS = None  # type: ignore[assignment, misc]
        DUCKDUCKGO_AVAILABLE = False


@dataclass
class WebSearchToolConfig:
    """Configuration for a web search tool.

    Attributes:
        provider: Search provider (currently only 'duckduckgo' supported)
        max_results: Maximum number of results to return
        description: Human-readable description for LLM tool selection
        timeout: Max seconds before search is cancelled
    """

    provider: str = "duckduckgo"
    max_results: int = 5
    description: str = ""
    timeout: int = 30


@dataclass
class WebSearchResult:
    """Result from executing a web search.

    Attributes:
        success: Whether the search succeeded
        results: List of search result dicts with title, href, body
        query: The search query used
        error: Error message if failed
    """

    success: bool
    results: list[dict[str, str]]
    query: str
    error: str | None = None


def execute_web_search(query: str, config: WebSearchToolConfig) -> WebSearchResult:
    """Execute a web search using the configured provider.

    Args:
        query: Search query string
        config: WebSearchToolConfig with provider settings

    Returns:
        WebSearchResult with search results or error
    """
    if not query or not query.strip():
        return WebSearchResult(
            success=False,
            results=[],
            query=query,
            error="Search query is empty",
        )

    if config.provider != "duckduckgo":
        return WebSearchResult(
            success=False,
            results=[],
            query=query,
            error=f"Unsupported provider: {config.provider}",
        )

    if not DUCKDUCKGO_AVAILABLE:
        return WebSearchResult(
            success=False,
            results=[],
            query=query,
            error="duckduckgo-search package not installed. Run: pip install duckduckgo-search",
        )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=config.max_results))

        logger.debug(f"Web search for '{query}' returned {len(results)} results")

        return WebSearchResult(
            success=True,
            results=results,
            query=query,
        )

    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return WebSearchResult(
            success=False,
            results=[],
            query=query,
            error=str(e),
        )


def format_search_results(result: WebSearchResult) -> str:
    """Format search results as readable text for LLM consumption.

    Args:
        result: WebSearchResult from execute_web_search

    Returns:
        Formatted string with results or error message
    """
    if not result.success:
        return f"Search error: {result.error}"

    if not result.results:
        return f"No results found for query: '{result.query}'"

    lines = [f"Search results for '{result.query}':\n"]

    for i, item in enumerate(result.results, 1):
        title = item.get("title", "No title")
        url = item.get("href", item.get("url", "No URL"))
        body = item.get("body", item.get("snippet", ""))

        lines.append(f"{i}. {title}")
        lines.append(f"   URL: {url}")
        if body:
            lines.append(f"   {body}")
        lines.append("")

    return "\n".join(lines)


class WebSearchInput(BaseModel):
    """Input schema for web search tool."""

    query: str = Field(description="The search query to look up on the web")


def create_web_search_tool(name: str, config: WebSearchToolConfig) -> StructuredTool:
    """Create a LangChain-compatible web search tool.

    Args:
        name: Tool name for LLM to reference
        config: WebSearchToolConfig with settings

    Returns:
        StructuredTool that can be used with LangChain agents
    """

    def search_func(query: str) -> str:
        """Execute web search and return formatted results."""
        result = execute_web_search(query, config)
        return format_search_results(result)

    description = (
        config.description or "Search the web for current information on any topic"
    )

    return StructuredTool.from_function(
        func=search_func,
        name=name,
        description=description,
        args_schema=WebSearchInput,
    )


def create_websearch_tool_from_config(
    name: str, tool_config: dict[str, Any]
) -> StructuredTool:
    """Create a web search tool from YAML config dict.

    This is the entry point used by the graph loader when parsing
    tool definitions from YAML.

    Args:
        name: Tool name
        tool_config: Dict with provider, max_results, description, etc.

    Returns:
        StructuredTool for use in agent nodes
    """
    config = WebSearchToolConfig(
        provider=tool_config.get("provider", "duckduckgo"),
        max_results=tool_config.get("max_results", 5),
        description=tool_config.get("description", ""),
        timeout=tool_config.get("timeout", 30),
    )

    return create_web_search_tool(name, config)


def parse_websearch_tools(tools_config: dict[str, Any]) -> dict[str, Any]:
    """Parse tools: section from YAML for websearch tools.

    Only parses tools with type: websearch.

    Args:
        tools_config: Dict from YAML tools: section

    Returns:
        Registry mapping tool names to LangChain StructuredTool objects
    """
    registry: dict[str, Any] = {}

    for name, config in tools_config.items():
        if config.get("type") != "websearch":
            continue

        registry[name] = create_websearch_tool_from_config(name, config)

    return registry
