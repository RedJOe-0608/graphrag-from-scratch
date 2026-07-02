# GraphRAG — Project Progress

A from-scratch GraphRAG system using local LLMs (Ollama), Qdrant (vector store), and Neo4j (knowledge graph).

## Architecture (planned pipeline)

```
PDF → Document → Chunks → EmbeddedChunks → VectorStore
                        → ExtractedKnowledge → GraphStore (Neo4j)
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
| App Configuration (`AppConfig`, `GraphSchema`) | Done |
| Entity/Relationship Extraction (Ollama, structured JSON) | Done, but **test currently broken** (see Known Issues) |
| Knowledge Graph (Neo4j) | Done |
| Ingestion → Vector Store Pipeline wiring | Not started (`main.py` still a disconnected dev harness) |
| Ingestion → Extraction → Graph Store wiring | Not started |
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

### Vector Store (`app/vector_store/`)
- **`vector_store.py`** — `VectorStore` ABC with `add(chunks)` and `search(query_embedding, limit) -> list[EmbeddedChunk]`
- **`qdrant_vector_store.py`** — `QdrantVectorStore` fully connects to Qdrant at `localhost:6333`. `add()`: lazy collection creation (cosine distance, vector size inferred from first chunk) + bulk upsert via `PointStruct`. `search()`: queries Qdrant via `query_points`, reconstructs `EmbeddedChunk` objects from payload. Both methods complete and passing tests.

### Configuration (`app/config/`, `config/`)
- **`app_config.py`** — dataclasses: `Neo4jConfig` (uri, username, password), `OllamaConfig` (model, host), `QdrantConfig` (host, port, collection), and top-level `AppConfig` bundling all three.
- **`app_config_loader.py`** — `load_app_config(path) -> AppConfig`; reads `config/app.yaml`.
- **`config/app.yaml`** — Neo4j (bolt://localhost:7687), Ollama (`qwen2.5:3b` model for extraction, host `http://localhost:11434`), Qdrant (localhost:6333, collection `graphrag`).
- **`graph_schema.py`** — `GraphSchema` dataclass: `entity_types: list[str]`, `relationship_types: list[str]`.
- **`graph_schema_loader.py`** — `load_graph_schema(path) -> GraphSchema`; reads `config/graph.yaml`.
- **`config/graph.yaml`** — allowed types: entities (Person, Organization, Location, Product, Event), relationships (WORKS_AT, LOCATED_IN, CREATED, OWNS).

### Graph Models (`app/graph/`)
- **`entity.py`** — `Entity` dataclass: `id`, `name`, `entity_type`, `description`.
- **`relationship.py`** — `Relationship` dataclass: `source` (entity id), `target` (entity id), `relationship_type`, `description`.
- **`extracted_knowledge.py`** — `ExtractedKnowledge` dataclass: `source_chunk: Chunk`, `entities: list[Entity]`, `relationships: list[Relationship]`.

### Extraction (`app/extraction/`)
- **`extractor.py`** — `Extractor` ABC with `extract(chunk) -> ExtractedKnowledge`.
- **`prompt_builder.py`** — `build_prompt(chunk, schema) -> str`; builds a detailed v1 prompt with numbered rules (allowed types only, snake_case IDs, unique IDs, valid relationship references, no invention, JSON-only, no markdown wrapping), embeds allowed entity/relationship types from `GraphSchema`, and a worked JSON example.
- **`ollama_extractor.py`** — `OllamaExtractor(config: OllamaConfig, schema: GraphSchema, client: Client | None = None)`. Calls Ollama chat API with `format=ExtractedKnowledgeResponse.model_json_schema()` for structured output, `temperature=0`. Validates response via Pydantic, raises `ValueError` with raw content on parse failure. Converts validated response into `Entity`/`Relationship` domain objects via `_build_entities`/`_build_relationships`.
- **`schemas/`** — Pydantic response models used only for Ollama structured-output validation (kept separate from the domain dataclasses in `app/graph/`):
  - `entity_response.py` — `EntityResponse(id, name, entity_type, description)`
  - `relationship_response.py` — `RelationshipResponse(source, target, relationship_type, description)`
  - `extracted_knowledge_response.py` — `ExtractedKnowledgeResponse(entities, relationships)`

### Knowledge Graph (`app/graph_store/`)
- **`graph_store.py`** — `GraphStore` ABC with `add(knowledge: ExtractedKnowledge)` and `clear()`.
- **`neo4j_graph_store.py`** — `Neo4jGraphStore(config: AppConfig, schema: GraphSchema)`. Connects via `neo4j.GraphDatabase.driver`, supports context manager (`__enter__`/`__exit__` closes driver). Creates a uniqueness constraint on `Entity.id` at init. `add()`: `MERGE`s entities in bulk (`UNWIND`), then merges each relationship individually with the relationship type interpolated into the Cypher query (validated against `schema.relationship_types` first — raises `ValueError` on unknown type, **not** an f-string injection risk since it's checked against an allowlist first). `clear()`: `MATCH (n) DETACH DELETE n`.

### Entry Point
- **`main.py`** — Currently a disconnected dev harness: instantiates `DoclingParser`, `DoclingChunker`, `OllamaEmbedder`, loads the graph schema and prints it. The actual parse → chunk → embed pipeline is commented out (pre-dates the extraction/graph work; not yet wired to extraction or either store).

---

## Not Started

Placeholder directories exist for all of these (empty, no code yet):

- **`app/retrieval/`** — hybrid retrieval (vector + graph)
- **`app/reranking/`** — cross-encoder or LLM-based reranker
- **`app/generation/`** — answer generation via Ollama LLM
- **`app/utils/`** — shared utilities
- **`app/database/`** — unclear purpose yet; empty, not referenced anywhere else in the codebase

No `IngestionPipeline` class exists yet — `main.py` calls each component ad hoc rather than through an orchestrating pipeline object. This is the top item on the roadmap.

---

## Known Issues / Where to Pick Up

1. **`tests/test_ollama_extractor.py` is broken.** It calls `OllamaExtractor(schema)`, but the constructor signature is `OllamaExtractor(config: OllamaConfig, schema: GraphSchema, client=None)` — `config` is missing. Confirmed failing with:
   ```
   TypeError: OllamaExtractor.__init__() missing 1 required positional argument: 'schema'
   ```
   Fix: load `AppConfig` via `load_app_config("config/app.yaml")` in the test and pass `config.ollama` (or the whole config, matching whatever the constructor expects) alongside the schema. This test is untracked (`git status` shows it as `??`), so it's mid-development, not a regression.
2. No test yet for `Neo4jGraphStore` (unlike the vector store, which has integration tests in `tests/test_vector_store.py`).
3. `main.py` and the two integration tests (`test_ingestion_pipeline.py`, `test_ollama_extractor.py`) each independently wire together components — there's no shared `IngestionPipeline` abstraction yet, so extraction/graph-store logic isn't part of the ingestion flow at all currently.
4. `StructuredDoclingDocument(Document)` uses inheritance, but violates LSP in practice: `DoclingChunker.chunk()` requires `docling_doc` to be non-null, so a plain `Document` (e.g. from `PDFParser`) can't safely be passed through the `Chunker` interface polymorphically — it'll raise `ValueError`. Not a bug today since `DoclingParser` output is always paired with `DoclingChunker`, but revisit (e.g. composition instead of inheritance, or a narrower interface) if the pipeline ever needs to pick a chunker generically at runtime rather than by construction.

---

## Dependencies (`requirements.txt`)

| Package | Purpose |
|---|---|
| `pymupdf` | PDF parsing (PDFParser) |
| `docling` | Layout-aware PDF parsing with table extraction (DoclingParser) |
| `transformers` | Tokenizer for token-accurate chunk size measurement |
| `ollama` | Embedding + extraction (structured JSON) + (future) answer generation |
| `qdrant-client` | Vector store |
| `neo4j` | Graph store driver |
| `pydantic` | Structured-output validation for Ollama extraction responses |
| `pyyaml` | Config + schema loading |

---

## Testing

- **`pytest.ini`** — sets `pythonpath = .` so `app.*` imports resolve when running pytest from the project root
- **`tests/conftest.py`** — shared `vector_store` fixture with uuid-based collection name; handles setup and teardown for both test files
- **`tests/data/sample_graphrag_document.pdf`** — test fixture PDF
- **`tests/test_ingestion_pipeline.py`** — integration test: parse → chunk → embed → `add()` + count assertion. Passing.
- **`tests/test_vector_store.py`** — integration tests for `add()` + `search()`: verifies collection creation, result structure (`EmbeddedChunk` fields), and empty-list no-op. Passing.
- **`tests/test_ollama_extractor.py`** — integration test for `OllamaExtractor.extract()`; asserts entities/relationships are extracted from a sample chunk about OpenAI/Sam Altman/Microsoft. **Currently failing** — see Known Issues above.
- Run tests with `pytest tests/ -v`

---

## Notes

- All major components follow an ABC + concrete implementation pattern, making them swappable.
- `SentenceChunker` retained as a lightweight fallback; `DoclingChunker` is the production path for complex PDFs.
- `DoclingParser` and `DoclingChunker` are paired — the structured Docling object flows between them via `StructuredDoclingDocument`.
- Extraction domain objects (`app/graph/entity.py`, `relationship.py`) are intentionally separate from the Pydantic response schemas (`app/extraction/schemas/`) — the latter exist only to constrain/validate Ollama's structured JSON output, then get converted into the former.
- `Neo4jGraphStore` takes the full `AppConfig` (not just `Neo4jConfig`) — inconsistent with `OllamaExtractor`, which takes just `OllamaConfig`. Worth deciding on one convention when building the `IngestionPipeline`.
- `main.py` is a dev harness, not a CLI or API entry point.
- `feature/entity-extraction` and `feature/graph-store` branches are both merged into `main` as of this update (PRs #8 and #9). Current branch is `main`.

---

## Roadmap (from HANDOFF.md)

1. **IngestionPipeline** ← next up
2. Integration tests
3. Entity resolution
4. Graph retriever
5. Vector retriever
6. Hybrid retrieval
7. RRF
8. Reranker
9. Context builder
10. Answer generation
11. GraphRAGEngine
