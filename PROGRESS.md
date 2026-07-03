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
| **Entity Resolution** — data model + storage + similarity search | **Phase 1 done, Phase 2 (resolver) next** |
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
- **`embedder.py`** — `Embedder` ABC. **Split into two abstract methods (2026-07-03, for entity resolution)**: `embed_chunk(chunks) -> list[EmbeddedChunk]` (renamed from `embed`, all call sites updated — `IngestionPipeline`, tests) and `embed_text(texts: list[str]) -> list[list[float]]` (new — embeds arbitrary text not tied to a `Chunk`; used for entity name+description embeddings).
- **`ollama_embedder.py`** — `OllamaEmbedder`; calls Ollama's `embed` API in a single batched request. Default model: `nomic-embed-text` (768-dim). Raises `RuntimeError` on `ResponseError`. Implements both `embed_chunk` and `embed_text`.

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
- **`entity.py`** — `Entity` dataclass: `id`, `name`, `entity_type`, `description`, **`aliases: list[str]`** (default via `field(default_factory=list)` — NOT a bare `[]`, which would be a shared-mutable-default bug), **`embedding: list[float] | None`** (default `None`; populated by the entity resolver, not the extractor). Also has module-level `build_entity_embedding_text(entity) -> str`, which builds `f"{name}. {description}"` (description `None`-safe via `or ""`) — the exact text that gets embedded for similarity search. Deliberately excludes `entity_type` from the embedded text (adds no discriminating signal, diluted the vector); type is used as a query-time filter instead.
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
- **`neo4j_graph_store.py`** — `Neo4jGraphStore(config: Neo4jConfig, schema: GraphSchema, embedding_dimensions: int)`. Connects via `neo4j.GraphDatabase.driver`, supports context manager (`__enter__`/`__exit__` closes driver). Creates a uniqueness constraint on `Entity.id` at init. `add()`: `MERGE`s entities in bulk (`UNWIND`), then merges each relationship individually with the relationship type interpolated into the Cypher query (validated against `schema.relationship_types` first — raises `ValueError` on unknown type, **not** an f-string injection risk since it's checked against an allowlist first). `clear()`: `MATCH (n) DETACH DELETE n`. **Fixed 2026-07-03**: the whole class body past `__init__`'s first line was mis-indented one level too deep, so `__enter__`/`__exit__`/`clear`/`add`/`_create_constraints`/`_merge_*` were all nested as local functions *inside* `__init__` instead of being class methods — `Neo4jGraphStore` couldn't be instantiated at all (`TypeError: Can't instantiate abstract class... without an implementation for 'add', 'clear'`). Re-indented; logic unchanged. Known partial-write caveat: `add()` merges entities and then relationships one at a time — if a later relationship in the loop fails, earlier entities/relationships for that chunk are already committed even though the pipeline records the whole chunk as a failure. Not yet addressed (would need one transaction per chunk, or upfront validation of all relationship types before writing anything).
  - **Entity resolution additions (2026-07-03)**:
    - `embedding_dimensions: int` constructor param — **not hardcoded** (matches `QdrantVectorStore`'s pattern of deriving vector size from a real embedding rather than a literal). Composition root should compute it once via `len(embedder.embed_text(["probe"])[0])` and pass it in; `Neo4jGraphStore` stays ignorant of *how* it was derived. Currently tested by passing `768` directly (matches `nomic-embed-text`'s real output size) — **composition root wiring not done yet**, see Where to Pick Up.
    - `_create_vector_index(dimensions)` — creates `entity_embedding` vector index (cosine similarity) on `Entity.embedding`, called from `__init__` after `_create_constraints()`. Verified `ONLINE` via `SHOW VECTOR INDEXES`.
    - `_merge_entities` now also writes `e.aliases` and `e.embedding`.
    - `find_similar_entities(entity_type, embedding, k=5) -> list[dict]` — **deliberately does NOT use the vector index.** Does exact cosine similarity (`vector.similarity.cosine`) over `MATCH (e:Entity {type: $entity_type})`, i.e. filter-by-type-first then brute-force score, `O(n)` over entities of that type. This was a deliberate choice over ANN-index-then-filter: Neo4j's `db.index.vector.queryNodes` finds top-k over the *whole* index before any type filter applies, which can starve results when one type dominates the index (post-filtering can return fewer than k, or wrong candidates, under type skew). Exact `MATCH`-first search avoids that correctness bug entirely at the cost of not using the ANN index. Comment left in code flagging the `O(n)` tradeoff as a deferred optimization. **Verified working** via ad hoc script: Sam Altman / Samuel Altman (Person) correctly ranked highest similarity to each other (0.88, 0.86) with Coca-Cola (Org) correctly excluded by the type filter.
    - The vector index itself (`entity_embedding`) is currently unused by any query — built for potential future use, not a wasted step.

### Entity Resolution — Design (locked in, 2026-07-03)

**Problem:** the LLM extractor generates entity ids/names independently per chunk (see `prompt_builder.py` — ids are only "unique within this response"). The same real-world entity mentioned across chunks can come out as different id/name strings (e.g. `sam_altman` vs `samuel_altman` vs `altman`), which `Neo4jGraphStore._merge_entities`'s exact-id `MERGE` won't catch — fragmenting the graph into duplicate nodes.

**Research finding:** Microsoft's official GraphRAG does **not** solve this — a maintainer confirmed in GitHub discussion #778 that real entity resolution "is not currently implemented... researching better approaches, no planned date." Vanilla GraphRAG only merges on exact `(title, type)` match. Neo4j's own tooling defers to dedicated ER engines (e.g. Senzing) rather than shipping embedding-threshold matching. Conclusion: no canonical similarity threshold exists in the literature — it's domain-tuned, and no single embedding-similarity score should be trusted alone.

**Locked-in approach — three-band decision, not a single threshold:**
1. Embed each entity as `name + description` (see `build_entity_embedding_text`), type excluded from the embedded text (used as a hard filter instead).
2. Blocking: filter candidates by `entity_type` first (cheap, exact), then similarity-rank within that block — avoids comparing e.g. a Person to a Product.
3. Three-band decision on the **top candidate's** similarity score:
   - `score ≥ HIGH` → confident match → auto-merge
   - `score < LOW` → confident non-match → create new node
   - `LOW ≤ score < HIGH` → ambiguous → escalate to a single LLM "same entity, yes/no?" adjudication call
   - Rationale: thresholds only **route** (easy-vs-ambiguous), they never **judge** — the risky decision is always either obviously easy or backstopped by an LLM, so no magic constant silently decides a real merge/no-merge outcome.
   - `HIGH`/`LOW` actual values **not chosen yet** — deferred to implementation time, no principled numbers derived so far beyond the qualitative "0.88 same-person / 0.86 aliased-person / would-be-lower for unrelated" sanity check.
4. **Candidate generation idea explored and rejected as the sole mechanism:** user proposed reusing chunk-level vector search (find 20 similar chunks, look at their entities as candidates) as blocking. Good instinct (reuses existing infra, cheap), but two gaps: (a) chunk similarity is *topical*, not *entity-identity* — a similar chunk can mention a completely different entity, so it's a noisier blocking signal than type-filtered entity-embedding search; (b) it requires chunk→entity provenance tracking, which doesn't exist yet (`_merge_entities` never records which chunk an entity came from). Current design uses direct entity-embedding similarity search instead (`find_similar_entities`), which needed no new provenance data.
5. **Description enrichment — explicitly NOT done from topically-similar chunks.** Reasoned through and rejected: enriching a not-yet-resolved entity's description using nearby chunks is circular (those chunks might be about a *different* same-named entity) and pollutes the very signal (description) that's supposed to disambiguate. Correct order: enrich (concatenate descriptions) only **after** a merge is confirmed, using descriptions already known to belong to the same resolved entity. **Locked in: concatenation, not LLM re-summarization**, for the merge step — simpler, revisit only if concatenated descriptions get unwieldy.
6. **Id ownership changes.** The LLM's entity `id` becomes a **local, per-extraction-call handle only** — never written to the graph as-is. The resolver assigns a canonical id (uuid) per entity: reused from the matched node if merging, freshly generated if new. Critically, **every relationship's `source`/`target` must then be rewritten through a `{local_id: canonical_id}` map before being handed to the graph store** — otherwise `_merge_relationship`'s `MATCH ... {id: $source}` silently finds nothing (Neo4j doesn't error, the edge is just never created). This was the trickiest concept to land during design discussion — worth re-explaining carefully if picked up by someone new to this codebase.
7. **Merge mechanics:** on merge, append new name to `aliases` (dedup guard), concatenate descriptions, **re-embed the node** on the merged form so its vector reflects the resolved entity (bounded/summary form preferred over an ever-growing blob, to avoid the embedding drifting generic — not yet implemented).
8. **Where resolution lives:** planned as a new `EntityResolver` component sitting between extraction and the graph store (`IngestionPipeline` calls it instead of `graph_store.add(knowledge)` directly) — keeps `Neo4jGraphStore` "dumb" (storage primitives only: search/fetch/write), resolver is the "brain" (decides merge vs new, builds id map, remaps relationships). Not built yet.
9. Resolution should run **per chunk, writing as it goes** (not batched at end of document) so later chunks in the same document can match against entities resolved from earlier chunks in that same run.

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
7. **Entity resolution — Phase 1 done, Phase 2 (the `EntityResolver` itself) is the next work.** See the full design writeup above under "Entity Resolution — Design." Concretely, next steps in order:
   - Scaffold `EntityResolver` (deps: `GraphStore`, `Embedder`, an LLM client for adjudication) + config for `HIGH`/`LOW` thresholds and `k`.
   - Band decision method: embed entity → `graph_store.find_similar_entities(...)` → look at top candidate's score → return `MERGE(id)` / `NEW` / `AMBIGUOUS(candidate)`.
   - LLM adjudicator for the `AMBIGUOUS` case only (small yes/no prompt).
   - Merge logic: append alias (dedup), concatenate descriptions, re-embed, update node.
   - **Id map + relationship remapping** — this is the part to be most careful implementing correctly; see design point #6 above for why it's easy to silently drop edges if skipped.
   - Wire into `IngestionPipeline`: replace direct `graph_store.add(knowledge)` with resolve-then-write, per chunk.
   - Composition root still needs updating too: `Neo4jGraphStore` now requires `embedding_dimensions` at construction — nothing currently computes and passes this in `main.py` or wherever the pipeline gets wired up. Compute once via `len(embedder.embed_text(["probe"])[0])`.
   - Manual end-to-end sanity run once wired (ingest a doc with a repeated/aliased entity, confirm one node not two, confirm relationships survive).

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
- `Neo4jGraphStore` takes `Neo4jConfig` + `GraphSchema` + (as of 2026-07-03) `embedding_dimensions: int` — the last one is a plain value, not a config object, deliberately computed once at the composition root rather than hardcoded (see Entity Resolution section). Still consistent in spirit with `OllamaExtractor`/`QdrantVectorStore` taking just their own config.
- `main.py` is a dev harness, not a CLI or API entry point; still not wired to `IngestionPipeline`.
- `feature/entity-extraction` and `feature/graph-store` branches are both merged into `main` as of this update (PRs #8 and #9). Current branch is `feature/ingestion-pipeline`.

---

## Roadmap (from HANDOFF.md)

1. ~~**IngestionPipeline**~~ — **done 2026-07-03**
2. ~~Integration tests~~ — deferred; building end-to-end first (see Testing note above)
3. **Entity resolution** ← in progress (Phase 1 done: data model, storage, similarity search. Phase 2 next: build `EntityResolver` — see Known Issues #7 and the design writeup above)
4. Graph retriever
5. Vector retriever
6. Hybrid retrieval
7. RRF
8. Reranker
9. Context builder
10. Answer generation
11. GraphRAGEngine
