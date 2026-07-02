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
| Entity/Relationship Extraction (Ollama, structured JSON, enum-constrained) | Done |
| Knowledge Graph (Neo4j) | Done |
| **IngestionPipeline** (parse → chunk → embed → vector store; extract → graph store) | **Done** |
| Hybrid Retrieval + RRF | Not started |
| Reranking | Not started |
| Answer Generation (Ollama LLM) | Not started |

**Testing note:** per user direction (2026-07-03), the project is prioritizing end-to-end functionality over test coverage for now — tests are fixed only when they block forward progress, not proactively expanded per feature. A dedicated testing pass will happen once the app works end-to-end.

---

## Completed

### Data Models (`app/models/`)
- **`document.py`** — `Document` dataclass: `id`, `title`, `text`
- **`structured_docling_document.py`** — `StructuredDoclingDocument` dataclass: extends `Document`, adds `docling_doc: DoclingDocument` for use with `DoclingChunker`
- **`chunk.py`** — `Chunk` dataclass: `id`, `document_id`, `text`
- **`embedded_chunk.py`** — `EmbeddedChunk` dataclass: wraps `Chunk` + `embedding: list[float]`

### Parsing (`app/parsing/`) — renamed from `app/ingestion/` on 2026-07-03 to free up that name for the pipeline orchestrator
- **`parser.py`** — `Parser` ABC with `parse(path) -> Document`
- **`pdf_parser.py`** — `PDFParser` using PyMuPDF (`fitz`); extracts text page-by-page, joins with newlines, assigns a UUID
- **`docling_parser.py`** — `DoclingParser` using Docling; layout-aware parsing with TableFormer for tables. OCR disabled (not needed for digital PDFs). Returns `StructuredDoclingDocument` with markdown export in `text` and the full `DoclingDocument` object in `docling_doc`.

### Ingestion Pipeline (`app/ingestion/`)
- **`ingestion_result.py`** — `IngestionResult` dataclass: `document`, `chunk_count`, `entity_count`, `relationship_count`, `failures: list[str]`. The final receipt returned once a document's full lifecycle (vector + graph) completes.
- **`ingestion_pipeline.py`** — `IngestionPipeline(parser, chunker, embedder, extractor, vector_store, graph_store)`, all six collaborators injected against their ABCs. `ingest(path) -> IngestionResult`:
  1. `parse → chunk → embed (batch) → vector_store.add` — vector-side flow, no error handling (a failure here has no natural partial-success mode).
  2. For each chunk: `extractor.extract(chunk)` then `graph_store.add(knowledge)`, both wrapped in one `try/except ValueError` — **skip-and-continue** per chunk (a bad chunk is recorded in `failures` and doesn't abort the document or the chunks around it).
  3. Assembles and returns `IngestionResult` with real entity/relationship counts (summed from `len(knowledge.entities/relationships)`, not per-chunk increments, since a chunk can yield zero-to-many of each).

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
- **`prompt_builder.py`** — `build_prompt(chunk, schema) -> str`; builds a detailed v1 prompt with numbered rules (allowed types only, snake_case IDs, unique IDs, valid relationship references, no invention, JSON-only, no markdown wrapping), embeds allowed entity/relationship types from `GraphSchema`, and a worked JSON example. **Fixed 2026-07-03**: the worked example used to show `"relationship_type": "CEO_OF"` — a value outside the default schema's allowed types — which the model (`qwen2.5:3b`) tended to imitate directly, overriding rule #2. Example now uses `WORKS_AT`, an actually-allowed type.
- **`ollama_extractor.py`** — `OllamaExtractor(config: OllamaConfig, schema: GraphSchema, client: Client | None = None)`. Builds `self.response_model` once at init via `build_extracted_knowledge_response(schema)` (schema-aware, enum-constrained). Calls Ollama chat API with `format=self.response_model.model_json_schema()`, `temperature=0`. Validates response via Pydantic, raises `ValueError` with raw content on parse/validation failure. Converts validated response into `Entity`/`Relationship` domain objects via `_build_entities`/`_build_relationships` (typed against `pydantic.BaseModel` now, since the response model is dynamic).
- **`schemas/`** — Pydantic response models used only for Ollama structured-output validation (kept separate from the domain dataclasses in `app/graph/`). **Reworked 2026-07-03** from static classes into schema-aware factory functions, so `entity_type`/`relationship_type` are constrained to `Literal[tuple(schema.entity_types)]` / `Literal[tuple(schema.relationship_types)]` — Ollama's structured-output JSON schema now has a real `enum`, so it's structurally impossible for the model to emit a type outside the configured graph schema (previously `str`, which only constrained shape, not value — this is what let `CEO_OF` through in the first place):
  - `entity_response.py` — `build_entity_response(entity_types) -> type[BaseModel]`
  - `relationship_response.py` — `build_relationship_response(relationship_types) -> type[BaseModel]`
  - `extracted_knowledge_response.py` — `build_extracted_knowledge_response(schema: GraphSchema) -> type[BaseModel]`, composes the two above.

### Knowledge Graph (`app/graph_store/`)
- **`graph_store.py`** — `GraphStore` ABC with `add(knowledge: ExtractedKnowledge)` and `clear()`.
- **`neo4j_graph_store.py`** — `Neo4jGraphStore(config: Neo4jConfig, schema: GraphSchema)`. Connects via `neo4j.GraphDatabase.driver`, supports context manager (`__enter__`/`__exit__` closes driver). Creates a uniqueness constraint on `Entity.id` at init. `add()`: `MERGE`s entities in bulk (`UNWIND`), then merges each relationship individually with the relationship type interpolated into the Cypher query (validated against `schema.relationship_types` first — raises `ValueError` on unknown type, **not** an f-string injection risk since it's checked against an allowlist first). `clear()`: `MATCH (n) DETACH DELETE n`. **Fixed 2026-07-03**: the whole class body past `__init__`'s first line was mis-indented one level too deep, so `__enter__`/`__exit__`/`clear`/`add`/`_create_constraints`/`_merge_*` were all nested as local functions *inside* `__init__` instead of being class methods — `Neo4jGraphStore` couldn't be instantiated at all (`TypeError: Can't instantiate abstract class... without an implementation for 'add', 'clear'`). Re-indented; logic unchanged. Known partial-write caveat: `add()` merges entities and then relationships one at a time — if a later relationship in the loop fails, earlier entities/relationships for that chunk are already committed even though the pipeline records the whole chunk as a failure. Not yet addressed (would need one transaction per chunk, or upfront validation of all relationship types before writing anything).

### Entry Point
- **`main.py`** — Still a disconnected dev harness: instantiates `DoclingParser`, `DoclingChunker`, `OllamaEmbedder`, loads the graph schema and prints it. Does not yet construct/call `IngestionPipeline`. Next cleanup: wire it to actually run the pipeline against a real path.

---

## Not Started

Placeholder directories exist for all of these (empty, no code yet):

- **`app/retrieval/`** — hybrid retrieval (vector + graph)
- **`app/reranking/`** — cross-encoder or LLM-based reranker
- **`app/generation/`** — answer generation via Ollama LLM
- **`app/utils/`** — shared utilities
- **`app/database/`** — unclear purpose yet; empty, not referenced anywhere else in the codebase

---

## Known Issues / Where to Pick Up

1. ~~`tests/test_ollama_extractor.py` broken constructor call~~ — **fixed 2026-07-03**: now loads `AppConfig`/`GraphSchema` and calls `OllamaExtractor(config=config.ollama, schema=schema)`.
2. No test yet for `Neo4jGraphStore` in isolation (covered indirectly via `test_ingestion_pipeline.py`'s `graph_store` fixture now). Per current testing priorities, not being actively added — see Testing section.
3. ~~No shared `IngestionPipeline` abstraction~~ — **done 2026-07-03**, see Completed above.
4. `StructuredDoclingDocument(Document)` uses inheritance, but violates LSP in practice: `DoclingChunker.chunk()` requires `docling_doc` to be non-null, so a plain `Document` (e.g. from `PDFParser`) can't safely be passed through the `Chunker` interface polymorphically — it'll raise `ValueError`. Not a bug today since `DoclingParser` output is always paired with `DoclingChunker`, but revisit (e.g. composition instead of inheritance, or a narrower interface) if the pipeline ever needs to pick a chunker generically at runtime rather than by construction.
5. `test_ollama_extractor.py` is flaky against small models: on a 2026-07-03 run, `qwen2.5:3b` failed to extract a `Microsoft` entity from a chunk describing "Microsoft invested billions of dollars into OpenAI" — plausibly because "invested" doesn't map cleanly onto any of the schema's allowed relationship types (`WORKS_AT`/`LOCATED_IN`/`CREATED`/`OWNS`), so the model may drop the entity rather than force an ill-fitting relationship. Not addressed yet (candidates: add an `INVESTED_IN` relationship type, or accept some entity-recall variance from a 3B model).
6. `Neo4jGraphStore.add()` isn't transactional per chunk — see note under Knowledge Graph above. If a relationship partway through a chunk's list fails validation, earlier entities/relationships for that chunk are already committed even though `IngestionPipeline` records the whole chunk as failed in `IngestionResult.failures`.

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

**Priority note (2026-07-03):** the project is now building end-to-end functionality first and deferring a dedicated testing pass until the whole app works — tests below are kept passing/unblocking as we go, but new test coverage isn't being proactively added per feature right now.

- **`pytest.ini`** — sets `pythonpath = .` so `app.*` imports resolve when running pytest from the project root
- **`tests/conftest.py`** — fixtures: `app_config` (loads `config/app.yaml` once), `graph_schema` (loads `config/graph.yaml` once), `vector_store` (depends on `app_config`, builds a `QdrantConfig` with a uuid-based test collection name via `dataclasses.replace`, handles setup/teardown), `graph_store` (depends on `app_config` + `graph_schema`, builds a real `Neo4jGraphStore`, calls `clear()` before/after since Neo4j has no per-test namespace like Qdrant's collections)
- **`tests/data/sample_graphrag_document.pdf`** — test fixture PDF
- **`tests/test_ingestion_pipeline.py`** — integration test: builds a real `IngestionPipeline` (DoclingParser/DoclingChunker/OllamaEmbedder/OllamaExtractor + the `vector_store`/`graph_store` fixtures), asserts on `IngestionResult` (`chunk_count > 0`, `entity_count > 0`, `failures` are strings) and on Qdrant's actual stored count. **Passing** — requires Ollama, Qdrant, and Neo4j all running locally.
- **`tests/test_vector_store.py`** — integration tests for `add()` + `search()`: verifies collection creation, result structure (`EmbeddedChunk` fields), and empty-list no-op. Passing.
- **`tests/test_ollama_extractor.py`** — integration test for `OllamaExtractor.extract()`; asserts entities/relationships are extracted from a sample chunk about OpenAI/Sam Altman/Microsoft. Constructor call fixed 2026-07-03; flaky on entity recall against a 3B model — see Known Issues #5.
- Run tests with `pytest tests/ -v` — needs Neo4j reachable at `bolt://localhost:7687` (e.g. `docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5`), Qdrant at `localhost:6333`, and Ollama at `localhost:11434` with `qwen2.5:3b` + an embedding model pulled.

---

## Notes

- All major components follow an ABC + concrete implementation pattern, making them swappable.
- `SentenceChunker` retained as a lightweight fallback; `DoclingChunker` is the production path for complex PDFs.
- `DoclingParser` and `DoclingChunker` are paired — the structured Docling object flows between them via `StructuredDoclingDocument`. `IngestionPipeline` doesn't enforce this pairing itself (any `Parser`/`Chunker` combo type-checks); pick compatible ones at construction time.
- Extraction domain objects (`app/graph/entity.py`, `relationship.py`) are intentionally separate from the Pydantic response schemas (`app/extraction/schemas/`) — the latter exist only to constrain/validate Ollama's structured JSON output, then get converted into the former. As of 2026-07-03 the schemas are built dynamically per `GraphSchema` (enum-constrained), not static classes.
- `Neo4jGraphStore` now takes just `Neo4jConfig` (fixed 2026-07-02, prior to this session), consistent with `OllamaExtractor` taking just `OllamaConfig` and `QdrantVectorStore` taking just `QdrantConfig`.
- `main.py` is a dev harness, not a CLI or API entry point; still not wired to `IngestionPipeline`.
- `feature/entity-extraction` and `feature/graph-store` branches are both merged into `main` as of this update (PRs #8 and #9). Current branch is `feature/ingestion-pipeline`.

---

## Roadmap (from HANDOFF.md)

1. ~~**IngestionPipeline**~~ — **done 2026-07-03**
2. ~~Integration tests~~ — deferred; building end-to-end first (see Testing note above)
3. **Entity resolution** ← next up
4. Graph retriever
5. Vector retriever
6. Hybrid retrieval
7. RRF
8. Reranker
9. Context builder
10. Answer generation
11. GraphRAGEngine
