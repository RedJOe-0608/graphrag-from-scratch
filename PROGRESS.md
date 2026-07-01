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
| Docling Parser + Chunker | Done |
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
- **`structured_docling_document.py`** — `StructuredDoclingDocument` dataclass: extends `Document`, adds `docling_doc: DoclingDocument` for use with `DoclingChunker`
- **`chunk.py`** — `Chunk` dataclass: `id`, `document_id`, `text`
- **`embedded_chunk.py`** — `EmbeddedChunk` dataclass: wraps `Chunk` + `embedding: list[float]`

### Ingestion (`app/ingestion/`)
- **`parser.py`** — `Parser` ABC with `parse(path) -> Document`
- **`pdf_parser.py`** — `PDFParser` using PyMuPDF (`fitz`); extracts text page-by-page, joins with newlines, assigns a UUID
- **`docling_parser.py`** — `DoclingParser` using Docling; layout-aware parsing with TableFormer for tables. OCR disabled (not needed for digital PDFs). Returns `StructuredDoclingDocument` with markdown export in `text` and the full `DoclingDocument` object in `docling_doc`.

### Chunking (`app/chunking/`)
- **`chunker.py`** — `Chunker` ABC with `chunk(document) -> list[Chunk]`
- **`sentence_chunker.py`** — `SentenceChunker`; naive period-split, strips blanks, assigns UUID per chunk. (No overlap or sliding window yet.)
- **`docling_chunker.py`** — `DoclingChunker`; uses Docling's `HybridChunker` with `nomic-embed-text` tokenizer. Structure-aware splitting (sections → paragraphs → sentences). Guaranteed max 512 tokens per chunk. Tables treated as atomic units. Requires `StructuredDoclingDocument` as input.

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
| `pymupdf` | PDF parsing (PDFParser) |
| `docling` | Layout-aware PDF parsing with table extraction (DoclingParser) |
| `transformers` | Tokenizer for token-accurate chunk size measurement |
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
- `SentenceChunker` retained as a lightweight fallback; `DoclingChunker` is the production path for complex PDFs.
- `DoclingParser` and `DoclingChunker` are paired — the structured Docling object flows between them via `StructuredDoclingDocument`.
- `main.py` is a dev harness, not a CLI or API entry point.
- `data/sample.pdf` is the test document used during development.
