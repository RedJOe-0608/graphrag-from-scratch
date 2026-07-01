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
| Vector Store (Qdrant) | Done |
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
- **`main.py`** — Instantiates PDFParser, SentenceChunker, OllamaEmbedder. Pipeline logic currently commented out (in-progress refactor to integrate vector store).

---

## In Progress

### Vector Store (`app/vector_store/`) — branch: `feature/search-vector-store`
- **`vector_store.py`** — `VectorStore` ABC with `add(chunks)` and `search(query_embedding, limit) -> list[EmbeddedChunk]`
- **`qdrant_vector_store.py`** — `QdrantVectorStore` fully connects to Qdrant at `localhost:6333`. `add()`: lazy collection creation (cosine distance, vector size inferred from first chunk) + bulk upsert via `PointStruct`. `search()`: queries Qdrant via `query_points`, reconstructs `EmbeddedChunk` objects from payload. Both methods complete and passing tests.

---

## Not Started

Placeholder directories exist for all of these (empty, no code yet):

- **`app/extraction/`** — entity/relation extraction from chunks
- **`app/graph/`** — Neo4j knowledge graph ingestion and querying
- **`app/retrieval/`** — hybrid retrieval (vector + graph)
- **`app/reranking/`** — cross-encoder or LLM-based reranker
- **`app/generation/`** — answer generation via Ollama LLM
- **`app/utils/`** — shared utilities

---

## Dependencies (`requirements.txt`)

| Package | Purpose |
|---|---|
| `pymupdf` | PDF parsing |
| `ollama` | Embedding + (future) LLM generation |
| `qdrant-client` | Vector store |

---

## Testing

- **`pytest.ini`** — sets `pythonpath = .` so `app.*` imports resolve when running pytest from the project root
- **`tests/conftest.py`** — shared `vector_store` fixture with uuid-based collection name; handles setup and teardown for both test files
- **`tests/data/sample_graphrag_document.pdf`** — test fixture PDF
- **`tests/test_ingestion_pipeline.py`** — integration test: parse → chunk → embed → `add()` + count assertion. Passing.
- **`tests/test_vector_store.py`** — integration tests for `add()` + `search()`: verifies collection creation, result structure (`EmbeddedChunk` fields), and empty-list no-op. Passing.
- Run tests with `pytest tests/ -v`

---

## Notes

- All major components follow an ABC + concrete implementation pattern, making them swappable.
- No semantic chunking yet — `SentenceChunker` is a placeholder; semantic chunking is a stated goal.
- `main.py` is a dev harness, not a CLI or API entry point.
- `data/sample.pdf` is the test document used during development.
