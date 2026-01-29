# RAG Example

Retrieval-Augmented Generation pipeline using YAMLGraph.

## Setup

```bash
# Install RAG dependencies
pip install yamlgraph[rag]

# Set OpenAI API key (required for embeddings)
export OPENAI_API_KEY=sk-...
```

## Quick Start

### 1. Run the Demo

```bash
cd examples/rag
./demo.sh "What is YAMLGraph?"
```

### 2. Manual Steps

```bash
cd examples/rag

# Index documents
python index_docs.py ./docs --collection test_docs --db-path ./vectorstore

# Run the pipeline
yamlgraph graph run graph.yaml -v question="What is YAMLGraph?"
```

**Note:** Must run from `examples/rag/` directory for local tool imports to work.

## Index Script Options

```bash
# Basic indexing
python index_docs.py ./docs --collection my_docs

# With custom chunking
python index_docs.py ./docs \
  --collection my_docs \
  --chunk-size 500 \
  --chunk-overlap 50

# Custom embedding model
python index_docs.py ./docs \
  --collection my_docs \
  --embedding-model text-embedding-3-large

# Custom database path
python index_docs.py ./docs \
  --collection my_docs \
  --db-path /path/to/vectorstore
```

## Collection Management

```bash
# List all collections
python index_docs.py --list

# Show collection info
python index_docs.py --info my_docs

# Delete a collection
python index_docs.py --delete my_docs
```

## How It Works

1. **Indexing** (`index_docs.py`):
   - Reads `.md` and `.txt` files from source folder
   - Chunks documents into smaller pieces
   - Generates embeddings via OpenAI
   - Stores in LanceDB (embedded vector database)

2. **Retrieval** (`rag_retrieve` tool):
   - Embeds the query using same model
   - Searches for similar chunks
   - Returns top-k results with scores

3. **Generation** (LLM node):
   - Receives retrieved context
   - Generates answer grounded in documents

## File Structure

```
examples/rag/
├── docs/                   # Sample documents to index
│   ├── about.md
│   └── features.md
├── index_docs.py           # Indexing script
├── graph.yaml              # RAG pipeline
├── prompts/
│   └── answer.yaml         # Answer generation prompt
└── README.md               # This file
```

## Customization

### Using Different Embedding Providers

Fork this example and modify `index_docs.py`:

```python
# Replace OpenAI with another provider
from your_provider import get_embedding

def embed_text(text: str, model: str) -> list[float]:
    return your_provider.embed(text)
```

Update the `rag_retrieve` tool call to match, or create your own tool.

### Using Different Vector Stores

Replace LanceDB with ChromaDB or another store:

1. Modify `index_docs.py` to use your store
2. Create a custom `python_tool` for retrieval
3. Update `graph.yaml` to use your tool

### Hybrid Search

For keyword + semantic search, extend the retrieval:

```python
# In a custom python_tool
def hybrid_retrieve(query: str, collection: str) -> list[dict]:
    semantic_results = rag_retrieve(collection, query)
    keyword_results = keyword_search(collection, query)
    return merge_and_rerank(semantic_results, keyword_results)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | For embeddings |

## Troubleshooting

### "Collection not found"

Run the indexing script first:
```bash
python index_docs.py ./docs --collection my_docs
```

### "Vector store not found"

The `./vectorstore/` directory must exist. Created automatically by indexing.

### Empty results

- Check your query matches document content
- Try lowering `top_k` threshold
- Verify documents were indexed: `python index_docs.py --info my_docs`
