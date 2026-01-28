"""RAG retrieve tool for vector store queries.

This module provides retrieval functionality for RAG (Retrieval-Augmented
Generation) pipelines. Uses LanceDB as the embedded vector store.

Usage in YAML graph:
    nodes:
      retrieve:
        type: tool
        tool: yamlgraph.tools.rag_retrieve
        args:
          collection: my_docs
          query: "{state.question}"
          top_k: 5
        state_key: context
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VectorStoreNotFoundError(Exception):
    """Raised when the vector store database path doesn't exist."""

    pass


class CollectionNotFoundError(Exception):
    """Raised when the requested collection doesn't exist."""

    pass


def rag_retrieve(
    collection: str,
    query: str,
    top_k: int = 5,
    threshold: float | None = None,
    db_path: str = "./vectorstore",
) -> list[dict[str, Any]]:
    """Retrieve relevant documents from a vector store collection.

    Args:
        collection: Name of the collection to search
        query: The search query text
        top_k: Maximum number of results to return (default 5)
        threshold: Minimum similarity score (0-1), filters results below this
        db_path: Path to the LanceDB database directory

    Returns:
        List of dicts with keys: content, source, score, metadata

    Raises:
        VectorStoreNotFoundError: If db_path doesn't exist
        CollectionNotFoundError: If collection doesn't exist
        ImportError: If lancedb is not installed
    """
    # Check db_path exists
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        raise VectorStoreNotFoundError(
            f"Vector store not found at '{db_path}'. "
            "Run the indexing script first to create the database."
        )

    # Import lancedb (optional dependency)
    try:
        import lancedb
    except ImportError as e:
        raise ImportError(
            "lancedb is required for RAG functionality. "
            "Install with: pip install yamlgraph[rag]"
        ) from e

    # Connect to database
    db = lancedb.connect(str(db_path_obj))

    # Check collection exists
    table_names = db.table_names()
    if collection not in table_names:
        raise CollectionNotFoundError(
            f"Collection '{collection}' not found. "
            f"Available collections: {', '.join(table_names) or 'none'}"
        )

    # Get embedding model from metadata
    embedding_model = _get_collection_metadata(db, collection, "embedding_model")
    if not embedding_model:
        embedding_model = "text-embedding-3-small"  # Default
        logger.warning(
            f"No embedding model found in collection metadata, using default: {embedding_model}"
        )

    # Get query embedding
    query_embedding = _get_embedding(query, embedding_model)

    # Search the collection
    table = db.open_table(collection)

    # LanceDB search - use to_arrow() instead of to_pandas() (no pandas dependency)
    results = table.search(query_embedding).limit(top_k).to_arrow()

    # Format results
    formatted = []
    for i in range(results.num_rows):
        # Get distance and convert to similarity score
        distance = results.column("_distance")[i].as_py()
        score = 1 - distance  # Convert distance to similarity

        # Apply threshold filter
        if threshold is not None and score < threshold:
            continue

        formatted.append(
            {
                "content": results.column("content")[i].as_py()
                if "content" in results.column_names
                else "",
                "source": results.column("source")[i].as_py()
                if "source" in results.column_names
                else "",
                "score": round(score, 4),
                "metadata": {
                    "chunk_index": results.column("chunk_index")[i].as_py()
                    if "chunk_index" in results.column_names
                    else None,
                },
            }
        )

    logger.info(f"Retrieved {len(formatted)} results from '{collection}'")
    return formatted


def _get_collection_metadata(
    db: Any,
    collection: str,
    key: str,
) -> str | None:
    """Get metadata value for a collection.

    Metadata is stored in a separate table: {collection}_metadata
    """
    metadata_table = f"{collection}_metadata"

    try:
        if metadata_table not in db.table_names():
            return None

        table = db.open_table(metadata_table)
        df = table.to_pandas()
        row = df[df["key"] == key]

        if row.empty:
            return None

        return row.iloc[0]["value"]
    except Exception as e:
        logger.debug(f"Could not read metadata: {e}")
        return None


def _get_embedding(text: str, model: str) -> list[float]:
    """Get embedding for text using OpenAI API.

    Args:
        text: Text to embed
        model: OpenAI embedding model name

    Returns:
        Embedding vector as list of floats
    """
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError(
            "openai is required for embeddings. Install with: pip install openai"
        ) from e

    client = OpenAI()
    response = client.embeddings.create(
        input=text,
        model=model,
    )

    return response.data[0].embedding


def rag_retrieve_node(state: dict[str, Any]) -> dict[str, Any]:
    """State-based wrapper for rag_retrieve for type: python nodes.

    Reads arguments from state keys:
    - rag_collection: Collection name (required)
    - rag_query: Search query (required)
    - rag_top_k: Number of results (default 5)
    - rag_threshold: Minimum score (optional)
    - rag_db_path: Database path (default ./vectorstore)

    Or from node args in state:
    - _node_args: dict with collection, query, top_k, etc.

    Returns:
        Dict with 'context' key containing retrieval results
    """
    # Check for node args (passed by graph loader)
    node_args = state.get("_node_args", {})

    collection = node_args.get("collection") or state.get("rag_collection")
    query = node_args.get("query") or state.get("rag_query")
    top_k = node_args.get("top_k") or state.get("rag_top_k", 5)
    threshold = node_args.get("threshold") or state.get("rag_threshold")
    db_path = node_args.get("db_path") or state.get("rag_db_path", "./vectorstore")

    if not collection:
        raise ValueError("rag_collection or args.collection required in state")
    if not query:
        raise ValueError("rag_query or args.query required in state")

    results = rag_retrieve(
        collection=collection,
        query=query,
        top_k=int(top_k),
        threshold=float(threshold) if threshold else None,
        db_path=db_path,
    )

    return {"context": results}
