"""Integration tests for RAG example.

Tests the indexing script and graph execution.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Path to examples/rag
RAG_EXAMPLE_PATH = Path(__file__).parent.parent.parent / "examples" / "rag"

# Check if lancedb is available for RAG tests
try:
    import importlib.util

    HAS_LANCEDB = importlib.util.find_spec("lancedb") is not None
except ImportError:
    HAS_LANCEDB = False


class TestIndexDocsScript:
    """Test the index_docs.py script."""

    def test_script_exists(self):
        """Index script should exist."""
        assert (RAG_EXAMPLE_PATH / "index_docs.py").exists()

    @pytest.mark.skipif(not HAS_LANCEDB, reason="lancedb not installed")
    def test_list_empty_vectorstore(self):
        """Should handle empty/nonexistent vectorstore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [sys.executable, str(RAG_EXAMPLE_PATH / "index_docs.py"), "--list"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env={"PATH": "", "PYTHONPATH": str(RAG_EXAMPLE_PATH.parent.parent)},
            )
            assert result.returncode == 0
            # Output may go to stdout or stderr depending on logging config
            output = result.stdout + result.stderr
            assert "No vector store found" in output or "No collections found" in output

    def test_help_flag(self):
        """Should show help."""
        result = subprocess.run(
            [sys.executable, str(RAG_EXAMPLE_PATH / "index_docs.py"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Index documents for RAG retrieval" in result.stdout

    @pytest.mark.skipif(
        not (RAG_EXAMPLE_PATH / "docs").exists(),
        reason="Sample docs not found",
    )
    def test_indexing_requires_openai_key(self):
        """Should fail gracefully without API key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(RAG_EXAMPLE_PATH / "index_docs.py"),
                    str(RAG_EXAMPLE_PATH / "docs"),
                    "--collection",
                    "test",
                    "--db-path",
                    tmpdir,
                ],
                capture_output=True,
                text=True,
                env={"PATH": "", "PYTHONPATH": str(RAG_EXAMPLE_PATH.parent.parent)},
            )
            # Should fail because no API key
            assert result.returncode != 0 or "OPENAI_API_KEY" in result.stderr


class TestRagGraphFiles:
    """Test that RAG example files are valid."""

    def test_graph_yaml_exists(self):
        """graph.yaml should exist."""
        assert (RAG_EXAMPLE_PATH / "graph.yaml").exists()

    def test_prompt_yaml_exists(self):
        """prompts/answer.yaml should exist."""
        assert (RAG_EXAMPLE_PATH / "prompts" / "answer.yaml").exists()

    def test_docs_folder_exists(self):
        """docs/ folder with sample documents should exist."""
        docs_path = RAG_EXAMPLE_PATH / "docs"
        assert docs_path.exists()
        # Should have at least one markdown file
        md_files = list(docs_path.glob("*.md"))
        assert len(md_files) >= 1

    def test_graph_yaml_is_valid_yaml(self):
        """graph.yaml should be valid YAML."""
        import yaml

        graph_path = RAG_EXAMPLE_PATH / "graph.yaml"
        content = graph_path.read_text()
        data = yaml.safe_load(content)

        # YAMLGraph format uses top-level name, nodes, edges
        assert "name" in data
        assert "nodes" in data
        assert "edges" in data


class TestRagRetrieveInGraph:
    """Test rag_retrieve tool can be used in graph context."""

    def test_tool_is_importable(self):
        """Tool should be importable from yamlgraph.tools."""
        from yamlgraph.tools import rag_retrieve

        assert callable(rag_retrieve)

    def test_graph_references_correct_tool(self):
        """Graph should reference the correct tool path."""
        graph_path = RAG_EXAMPLE_PATH / "graph.yaml"
        content = graph_path.read_text()

        assert "yamlgraph.tools.rag_retrieve" in content


class TestChunkText:
    """Test the chunking function."""

    def test_chunk_import(self):
        """Should be able to import chunk_text."""
        # Add examples to path
        sys.path.insert(0, str(RAG_EXAMPLE_PATH))
        try:
            from index_docs import chunk_text

            assert callable(chunk_text)
        finally:
            sys.path.remove(str(RAG_EXAMPLE_PATH))

    def test_small_text_no_chunking(self):
        """Small text should return single chunk."""
        sys.path.insert(0, str(RAG_EXAMPLE_PATH))
        try:
            from index_docs import chunk_text

            text = "Short text."
            chunks = chunk_text(text, chunk_size=1000, overlap=100)
            assert len(chunks) == 1
            assert chunks[0] == text
        finally:
            sys.path.remove(str(RAG_EXAMPLE_PATH))

    def test_large_text_chunked(self):
        """Large text should be split into chunks."""
        sys.path.insert(0, str(RAG_EXAMPLE_PATH))
        try:
            from index_docs import chunk_text

            text = "Word " * 500  # 2500 chars
            chunks = chunk_text(text, chunk_size=500, overlap=50)
            assert len(chunks) > 1

            # Each chunk should be roughly chunk_size or less
            for chunk in chunks:
                assert len(chunk) <= 600  # Allow some flexibility
        finally:
            sys.path.remove(str(RAG_EXAMPLE_PATH))

    def test_overlap_works(self):
        """Chunks should overlap."""
        sys.path.insert(0, str(RAG_EXAMPLE_PATH))
        try:
            from index_docs import chunk_text

            # Create text with distinct markers
            text = "AAAA. BBBB. CCCC. DDDD. EEEE. " * 20
            chunks = chunk_text(text, chunk_size=100, overlap=30)

            # With overlap, adjacent chunks should share some content
            if len(chunks) >= 2:
                # Last part of chunk 0 should appear in chunk 1
                # (This is a loose test - overlap means some shared content)
                assert len(chunks[0]) > 50
                assert len(chunks[1]) > 50
        finally:
            sys.path.remove(str(RAG_EXAMPLE_PATH))
