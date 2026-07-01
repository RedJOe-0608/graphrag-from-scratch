# GraphRAG — Project Progress

A from-scratch GraphRAG system using local LLMs (Ollama), Qdrant (vector store), and Neo4j (knowledge graph).

## Architecture (planned pipeline)

```
PDF → Document → Chunks → EmbeddedChunks → VectorStore
                                          ↓
                              Hybrid Retrieval (vector + graph)
                                          ↓
                              RRF → Reranker → LLM → Answer
```

---

## Status Overview

| Phase | Status |
|---|---|
| Document Ingestion | Done |
| Data Models | Done |
| Sentence Chunking | Done |
| Embedding (Ollama) | Done |
| Vector Store (Qdrant) | In Progress |
| Knowledge Graph (Neo4j) | Not started |
| Hybrid Retrieval + RRF | Not started |
| Reranking | Not started |
| Answer Generation (Ollama LLM) | Not started |

---

## Completed

### Data Models (`app/models/`)
- **`document.py`** — `Document` dataclass: `id`, `title`, `text`
- **`chunk.py`** — `Chunk` dataclass: `id`, `document_id`, `text`
- **`embedded_chunk.py`** — `EmbeddedChunk` dataclass: wraps `Chunk` + `embedding: list[float]`

### Ingestion (`app/ingestion/`)
- **`parser.py`** — `Parser` ABC with `parse(path) -> Document`
- **`pdf_parser.py`** — `PDFParser` using PyMuPDF (`fitz`); extracts text page-by-page, joins with newlines, assigns a UUID

### Chunking (`app/chunking/`)
- **`chunker.py`** — `Chunker` ABC with `chunk(document) -> list[Chunk]`
- **`sentence_chunker.py`** — `SentenceChunker`; naive period-split, strips blanks, assigns UUID per chunk. (No overlap or sliding window yet.)

### Embedding (`app/embeddings/`)
- **`embedder.py`** — `Embedder` ABC with `embed(chunks) -> list[EmbeddedChunk]`
- **`ollama_embedder.py`** — `OllamaEmbedder`; calls Ollama's `embed` API in a single batched request. Default model: `nomic-embed-text`. Raises `RuntimeError` on `ResponseError`.

### Entry Point
- **`main.py`** — Wires PDFParser → SentenceChunker → OllamaEmbedder and prints the first embedded chunk. Used for manual smoke-testing.

---

## In Progress

### Vector Store (`app/vector_store/`) — branch: `feature/vector-store`
- **`vector_store.py`** — `VectorStore` ABC with `add(chunks)` and `search(query_embedding, limit) -> list[EmbeddedChunk]`
- **`qdrant_vector_store.py`** — `QdrantVectorStore` constructor done (connects to Qdrant at `localhost:6333`, collection `documents`). **`add` and `search` methods not yet implemented.**

---

## Not Started

Placeholder directories exist for all of these (empty, no code yet):

- **`app/extraction/`** — entity/relation extraction from chunks
- **`app/graph/`** — Neo4j knowledge graph ingestion and querying
- **`app/retrieval/`** — hybrid retrieval (vector + graph)
- **`app/reranking/`** — cross-encoder or LLM-based reranker
- **`app/generation/`** — answer generation via Ollama LLM
- **`app/database/`** — DB layer (purpose TBD)
- **`app/utils/`** — shared utilities
- **`tests/`** — test suite (directory exists, no tests written)

---

## Dependencies (`requirements.txt`)

| Package | Purpose |
|---|---|
| `pymupdf` | PDF parsing |
| `ollama` | Embedding + (future) LLM generation |
| `qdrant-client` | Vector store |

---

## Notes

- All major components follow an ABC + concrete implementation pattern, making them swappable.
- No semantic chunking yet — `SentenceChunker` is a placeholder; semantic chunking is a stated goal.
- `main.py` is a dev harness, not a CLI or API entry point.
- `data/sample.pdf` is the test document used during development.
