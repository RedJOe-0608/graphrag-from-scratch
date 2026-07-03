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
| **IngestionPipeline** (parse → chunk → embed → vector store; extract → resolve → graph store) | **Done** |
| **Entity Resolution** — `EntityResolver`, multi-candidate LLM matching, provenance | **Done (Phase 1 + Phase 2)** |
| **Relationship quality** — enriched schema (endpoints) + endpoint-type validation | **Done** |
| **OpenAI extraction + matching** (`gpt-4o` / `gpt-4o-mini`) | **Done** |
| **Vector retriever** (`Retriever` ABC + `VectorRetriever`) | **Done** |
| **Graph retriever** (`GraphRetriever`, `QueryEntityExtractor`) | **Done** |
| **Hybrid Retrieval + RRF** (`HybridRetriever`) | **Done** |
| Reranking | Deferred (see Roadmap) |
| **Context Builder + Answer Generation** (`build_context`, `OpenAIAnswerGenerator`) | **Done** |
| **GraphRAGEngine** (facade over ingestion + hybrid retrieval + generation) | **Done** |

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
- **`ingestion_pipeline.py`** — `IngestionPipeline(parser, chunker, embedder, extractor, vector_store, resolver)` — **now takes an `EntityResolver` instead of a `GraphStore`** (the resolver holds the graph store). `ingest(path) -> IngestionResult`:
  1. `parse → chunk → embed (batch) → vector_store.add` — vector-side flow, no error handling.
  2. For each chunk: `extractor.extract(chunk)` then `resolver.resolve_knowledge(knowledge)` (resolve-then-write per chunk), wrapped in `try/except ValueError` — **skip-and-continue**. `relationship_count` uses the count of relationships actually written by the resolver.
  3. Assembles and returns `IngestionResult`.

### Chunking (`app/chunking/`)
- **`chunker.py`** — `Chunker` ABC with `chunk(document) -> list[Chunk]`
- **`sentence_chunker.py`** — `SentenceChunker`; naive period-split, strips blanks, assigns UUID per chunk. (No overlap or sliding window yet.)
- **`docling_chunker.py`** — `DoclingChunker`; uses Docling's `HybridChunker` with `nomic-embed-text` tokenizer. Structure-aware splitting (sections → paragraphs → sentences). Guaranteed max 512 tokens per chunk. Tables treated as atomic units. Requires `StructuredDoclingDocument` as input.

### Embedding (`app/embeddings/`)
- **`embedder.py`** — `Embedder` ABC. **Split into two abstract methods (2026-07-03, for entity resolution)**: `embed_chunk(chunks) -> list[EmbeddedChunk]` (renamed from `embed`, all call sites updated — `IngestionPipeline`, tests) and `embed_text(texts: list[str]) -> list[list[float]]` (new — embeds arbitrary text not tied to a `Chunk`; used for entity name+description embeddings).
- **`ollama_embedder.py`** — `OllamaEmbedder`; calls Ollama's `embed` API in a single batched request. Default model: `nomic-embed-text` (768-dim). Raises `RuntimeError` on `ResponseError`. Implements both `embed_chunk` and `embed_text`.

### Vector Store (`app/vector_store/`)
- **`vector_store.py`** — `VectorStore` ABC with `add(chunks)` and `search(query_embedding, limit) -> list[EmbeddedChunk]`
- **`qdrant_vector_store.py`** — `QdrantVectorStore` fully connects to Qdrant at `localhost:6333`. `add()`: lazy collection creation (cosine distance, vector size inferred from first chunk) + bulk upsert via `PointStruct`. `search()`: queries Qdrant via `query_points`, reconstructs `EmbeddedChunk` objects from payload. Both methods complete and passing tests. **`get_by_ids(chunk_ids) -> list[Chunk]`** (added 2026-07-04, for the graph retriever) — fetch-by-id via Qdrant's `retrieve()` (not similarity search), returns plain `Chunk`s (no embedding needed by callers). New abstract method on `VectorStore` too.

### Configuration (`app/config/`, `config/`)
- **`app_config.py`** — dataclasses: `Neo4jConfig` (uri, username, password), `OllamaConfig` (model, host), `QdrantConfig` (host, port, collection), and top-level `AppConfig` bundling all three.
- **`app_config_loader.py`** — `load_app_config(path) -> AppConfig`; reads `config/app.yaml`.
- **`config/app.yaml`** — Neo4j (bolt://localhost:7687), Ollama (`qwen2.5:3b`, host `http://localhost:11434` — now used for the **fallback** extractor/matcher; embeddings use `nomic-embed-text`), Qdrant (localhost:6333, collection `graphrag`). **Production extraction/matching runs on OpenAI** (`gpt-4o`), wired directly in `main.py` with the key read from `.env` (`OPENAI_API_KEY`, gitignored) — not from `app.yaml`.
- **`graph_schema.py`** — `RelationshipEndpoints` dataclass (`source: list[str]`, `target: list[str]`) + `GraphSchema` dataclass: `entity_types: list[str]`, `relationship_types: list[str]` (names only — kept flat so the extraction enum and graph-store allowed-set consume it unchanged), **`relationship_endpoints: dict[str, RelationshipEndpoints]`** (legal source/target entity types per relationship, used for endpoint-type validation).
- **`graph_schema_loader.py`** — `load_graph_schema(path) -> GraphSchema`; parses `config/graph.yaml`'s relationship dict into the name list + endpoints map.
- **`config/graph.yaml`** — **enriched (2026-07-03)** from 4 → 12 relationship types, each declaring its `source`/`target` endpoint entity types. Entities: Person, Organization, Location, Product, Event. Relationships: WORKS_AT, LOCATED_IN, CREATED, OWNS, INVESTED_IN, PARTNERED_WITH, BOARD_MEMBER_OF, ACQUIRED, DISTRIBUTES, SUPPLIES, SPOKE_AT, ATTENDED. The extra types were added after observing the coarse 4-type set force distinct relations (investor stake, board seat, manufacturing partner) into `OWNS`/`WORKS_AT` catch-alls.

### Graph Models (`app/graph/`)
- **`entity.py`** — `Entity` dataclass: `id`, `name`, `entity_type`, `description`, **`aliases: list[str]`** (`field(default_factory=list)`), **`embedding: list[float] | None`** (populated by the resolver), **`source_chunk_ids: list[str]`** (`field(default_factory=list)` — provenance: which chunk(s) the entity came from; stamped `[chunk.id]` at extraction, unioned on merge; for future citation/debugging). Module-level `build_entity_embedding_text(entity) -> str` builds `f"{name}. {description}"` — the text embedded for similarity search (type deliberately excluded, used as a query-time filter instead).
- **`relationship.py`** — `Relationship` dataclass: `source` (entity id), `target` (entity id), `relationship_type`, `description`.
- **`extracted_knowledge.py`** — `ExtractedKnowledge` dataclass: `source_chunk: Chunk`, `entities: list[Entity]`, `relationships: list[Relationship]`.

### Extraction (`app/extraction/`)
- **`extractor.py`** — `Extractor` ABC with `extract(chunk) -> ExtractedKnowledge`.
- **`prompt_builder.py`** — `build_prompt(chunk, schema) -> str`; numbered rules + allowed types from `GraphSchema` + a worked JSON example. **Rule 5 strengthened (2026-07-03)** to force relationships to reference declared entities. **Rule 11 added (2026-07-03)** requires every entity to include a `description` (one or two sentences, grounded only in the text).
- **`openai_extractor.py`** — **`OpenAIExtractor(schema, model="gpt-4o-mini", api_key=None)`** — the production extraction path (main.py uses `gpt-4o`). Uses OpenAI structured output (`beta.chat.completions.parse` with `build_extracted_knowledge_response(schema)`), `temperature=0`. Far better than the 3B: emits real descriptions, correct types, no example-copying (the 3B hallucinated `Sam Altman`/`OpenAI` from the prompt example). Relationships built via the shared `build_valid_relationships` validator.
- **`ollama_extractor.py`** — `OllamaExtractor(config, schema, client=None)` — the local fallback, same structured-output pattern via Ollama. Also uses `build_valid_relationships`. Left working but not the default path.
- **`relationship_validation.py`** — **`build_valid_relationships(validated_response, entities, schema)`** — shared by both extractors. Drops a relationship if (1) **self-consistency**: source/target isn't a declared entity in the chunk (no dangling refs Neo4j would silently drop), or (2) **endpoint types**: the source/target entity types aren't legal for the relationship type per `schema.relationship_endpoints` (e.g. a `WORKS_AT` pointing at a `Location` is dropped). This is what makes the extractor emit only valid, self-consistent knowledge.
- **`schemas/`** — dynamic, enum-constrained Pydantic response models (`build_entity_response`, `build_relationship_response`, `build_extracted_knowledge_response`). **`entity_response.description` is now required (`(str, ...)`)** so the model cannot omit it. `entity_type`/`relationship_type` are `Literal[tuple(...)]` enums, so structurally impossible to emit a type outside the schema.
- **`schemas/`** — Pydantic response models used only for Ollama structured-output validation (kept separate from the domain dataclasses in `app/graph/`). **Reworked 2026-07-03** from static classes into schema-aware factory functions, so `entity_type`/`relationship_type` are constrained to `Literal[tuple(schema.entity_types)]` / `Literal[tuple(schema.relationship_types)]` — Ollama's structured-output JSON schema now has a real `enum`, so it's structurally impossible for the model to emit a type outside the configured graph schema (previously `str`, which only constrained shape, not value — this is what let `CEO_OF` through in the first place):
  - `entity_response.py` — `build_entity_response(entity_types) -> type[BaseModel]`
  - `relationship_response.py` — `build_relationship_response(relationship_types) -> type[BaseModel]`
  - `extracted_knowledge_response.py` — `build_extracted_knowledge_response(schema: GraphSchema) -> type[BaseModel]`, composes the two above.

### Knowledge Graph (`app/graph_store/`)
- **`graph_store.py`** — `GraphStore` ABC. Methods: `add(knowledge)`, `clear()`, and (added for entity resolution) **`find_similar_entities(entity_type, embedding, k=5) -> list[dict]`**, **`upsert_entity(entity)`** (create/update one entity by id), **`add_relationship(relationship)`** (create/update one edge), **`get_relationships(entity_id) -> list[dict]`** (a node's edges as `{direction, type, other_name}` — used to feed candidate structure to the matcher).
- **`neo4j_graph_store.py`** — `Neo4jGraphStore(config: Neo4jConfig, schema: GraphSchema, embedding_dimensions: int)`. Connects via `neo4j.GraphDatabase.driver`, supports context manager (`__enter__`/`__exit__` closes driver). Creates a uniqueness constraint on `Entity.id` at init. `add()`: `MERGE`s entities in bulk (`UNWIND`), then merges each relationship individually with the relationship type interpolated into the Cypher query (validated against `schema.relationship_types` first — raises `ValueError` on unknown type, **not** an f-string injection risk since it's checked against an allowlist first). `clear()`: `MATCH (n) DETACH DELETE n`. **Fixed 2026-07-03**: the whole class body past `__init__`'s first line was mis-indented one level too deep, so `__enter__`/`__exit__`/`clear`/`add`/`_create_constraints`/`_merge_*` were all nested as local functions *inside* `__init__` instead of being class methods — `Neo4jGraphStore` couldn't be instantiated at all (`TypeError: Can't instantiate abstract class... without an implementation for 'add', 'clear'`). Re-indented; logic unchanged. Known partial-write caveat: `add()` merges entities and then relationships one at a time — if a later relationship in the loop fails, earlier entities/relationships for that chunk are already committed even though the pipeline records the whole chunk as a failure. Not yet addressed (would need one transaction per chunk, or upfront validation of all relationship types before writing anything).
  - **Entity resolution additions (2026-07-03)**:
    - `embedding_dimensions: int` constructor param — **not hardcoded** (matches `QdrantVectorStore`'s pattern of deriving vector size from a real embedding rather than a literal). Composition root should compute it once via `len(embedder.embed_text(["probe"])[0])` and pass it in; `Neo4jGraphStore` stays ignorant of *how* it was derived. Currently tested by passing `768` directly (matches `nomic-embed-text`'s real output size) — **composition root wiring not done yet**, see Where to Pick Up.
    - `_create_vector_index(dimensions)` — creates `entity_embedding` vector index (cosine similarity) on `Entity.embedding`, called from `__init__` after `_create_constraints()`. Verified `ONLINE` via `SHOW VECTOR INDEXES`.
    - `_merge_entities` now also writes `e.aliases`, `e.embedding`, and `e.source_chunk_ids`.
    - **`upsert_entity(entity)`** reuses `_merge_entities` with a single-item list; **`add_relationship(relationship)`** reuses `_merge_relationship`; **`get_relationships(entity_id)`** does a bidirectional `MATCH (e)-[r]-(other)` returning `{type, direction, other_name}`. These three are the storage primitives the `EntityResolver` composes.
    - `find_similar_entities(entity_type, embedding, k=5) -> list[dict]` (now also returns `source_chunk_ids`) — **deliberately does NOT use the vector index.** Does exact cosine similarity (`vector.similarity.cosine`) over `MATCH (e:Entity {type: $entity_type})`, i.e. filter-by-type-first then brute-force score, `O(n)` over entities of that type. This was a deliberate choice over ANN-index-then-filter: Neo4j's `db.index.vector.queryNodes` finds top-k over the *whole* index before any type filter applies, which can starve results when one type dominates the index (post-filtering can return fewer than k, or wrong candidates, under type skew). Exact `MATCH`-first search avoids that correctness bug entirely at the cost of not using the ANN index. Comment left in code flagging the `O(n)` tradeoff as a deferred optimization. **Verified working** via ad hoc script: Sam Altman / Samuel Altman (Person) correctly ranked highest similarity to each other (0.88, 0.86) with Coca-Cola (Org) correctly excluded by the type filter.
    - The vector index itself (`entity_embedding`) is currently unused by any query — built for potential future use, not a wasted step.

### Entity Resolution — Design (original, 2026-07-03) — ⚠️ SUPERSEDED

> This is the *original locked-in design*, kept for the reasoning/rationale. **The actual implementation diverged** (no auto-merge band, multi-candidate matching, LLM-picks-id not yes/no, OpenAI not 3B) — see **"Entity Resolution — Implemented"** below for what was really built and *why* it diverged. Read that section for current behavior; read this one for the original reasoning.

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

### Entity Resolution — Implemented (`app/resolution/`, 2026-07-03)

Phase 2 built and validated end-to-end across two documents. **The implementation diverged significantly from the original three-band design above** — the divergences were driven by testing, and are the important part to read:

- **`EntityResolver(graph_store, embedder, matcher, low_threshold, k=5)`** — the "brain" between extraction and the graph store. `IngestionPipeline` now holds a resolver (not a graph store directly) and calls `resolver.resolve_knowledge(knowledge)` per chunk.
- **`resolve_knowledge(knowledge)`** — resolves every entity to a canonical id (building a `{local_id: canonical_id}` map), then rewrites each relationship's `source`/`target` through that map before writing (design point #6 — the trickiest part; skip it and Neo4j silently drops edges). Also renders each entity's chunk relationships as text to feed the matcher.
- **`resolve(entity, entity_relationships, source_text)`** — the flow that replaced the three-band logic:
  1. Embed `name + description`, `find_similar_entities(k=5)`.
  2. Filter to **plausible** candidates (`score >= low_threshold`). None → new node (no LLM call).
  3. Otherwise hand ALL plausible candidates to the matcher, which returns the matching candidate's id or `None` → merge or create.
- **`_merge`** — appends alias (dedup), concatenates descriptions, unions `source_chunk_ids`, re-embeds on the merged form, upserts.

**Key divergences from the locked-in design, and why (all test-driven):**
1. **No HIGH auto-merge band.** Observed similarity scores for *true* vs *false* merges overlap (a wrong `Toronto→Austin` merge scored 0.907, higher than some correct `Northwind` merges at ~0.85) — so **no threshold can safely auto-merge**. `low_threshold` only filters out implausible candidates; the LLM is the sole arbiter for anything plausible. Effectively a two-tier (filter → LLM) design, not three-band.
2. **Multi-candidate, not single-candidate.** `k=1` failed because when descriptions diverge across chunks, the true match often isn't rank-1 (e.g. a 2nd "Renata Osei" mention's nearest neighbor was "Sam Whitfield"). So the matcher sees the **top-k** and picks among them.
3. **Matcher returns a candidate id (enum-constrained), not a yes/no.** See matchers below.
4. **Structural context matters most.** The matcher is fed the new entity's chunk relationships + source text AND each candidate's graph relationships (`get_relationships`). Relationships — not description — are what disambiguate same-name entities (two "Sarah Kim" PMs at different employers). The single biggest quality lever was **richer relationships** (the extractor fix tripled relationship density, which fixed the last marginal merge errors).
5. **Model capability is the ceiling, not prompts.** `qwen2.5:3b` could not do the matching judgment at all (said "not same" to everything, fragmenting the graph) — no prompt wording fixed it. Switching the matcher to OpenAI `gpt-4o-mini` fixed it immediately; `gpt-4o` additionally resolves hard org-abbreviation cases (`Solvane` = `Solvane Energy`).

**Matcher (`EntityMatcher` ABC + `match_entity(entity, entity_relationships, source_text, candidates, candidate_relationships) -> str | None`):**
- **`OpenAIEntityMatcher(model="gpt-4o-mini")`** (production) and **`OllamaEntityMatcher(config)`** (local fallback).
- **`match_response.py`** — `build_match_response(candidate_ids)` returns a Pydantic model whose `match` field is `Literal[tuple(candidate_ids + ["none"])]`. Constrained decoding makes it **structurally impossible** for the LLM to return an id that isn't a real candidate — no uuid-transcription errors. Returns `"none"` → no match.
- **`match_prompt.py`** — shared `build_match_prompt`; lays out the new entity (name/type/description/relationships/source passage) against the numbered candidates, and frames the call as "these are already similar, so likely the same unless a genuine conflict."

### Retrieval (`app/retrieval/`, 2026-07-04)
- **`retriever.py`** — `Retriever` ABC: `retrieve(query, limit=5) -> list[Chunk]`, most relevant first. Both retrievers below implement this same contract so they're interchangeable — deliberate, since hybrid retrieval (next roadmap item) will hold a `list[Retriever]` and fuse their outputs with RRF, which requires both sides to return the same item type (chunks, not entities or subgraphs).
- **`vector_retriever.py`** — `VectorRetriever(vector_store, embedder)`. `retrieve()`: embeds the query, `vector_store.search()`, strips `EmbeddedChunk` down to `Chunk`. Verified end-to-end against Qdrant.
- **`graph_retriever.py`** — `GraphRetriever(graph_store, vector_store, embedder, query_extractor, k=5)`. This is the "entity-anchored traversal" pattern (the classic GraphRAG local-search shape), reusing storage primitives already built for entity resolution rather than introducing new ones. `retrieve(query, limit)`:
  1. `query_extractor.extract(query)` → query entities (name + type only, see `QueryEntityExtractor` below).
  2. For each query entity: embed `name + description`, `graph_store.find_similar_entities(entity_type, embedding, k)` → up to `k` **anchor** nodes (type-filtered, no threshold — unlike `EntityResolver`, there's no LLM adjudication step here; a wrong anchor just adds ranking noise, not graph corruption).
  3. For each anchor: `graph_store.get_relationships(anchor_id)` → **1-hop neighbors** (deliberately not 2+ hops — each additional hop re-runs the full fan-out query on every node touched by the last round, and Microsoft GraphRAG's local search also defaults to 1 hop; revisit only if 1-hop context proves too shallow in practice).
  4. Tallies every `source_chunk_ids`/`other_source_chunk_ids` seen across anchors + neighbors in a `Counter` — frequency is the ranking signal (a chunk referenced by more anchors/neighbors ranks higher). `k` (anchor fan-out width) and `limit` (final chunk count returned) are different knobs operating at different stages — `k` shapes what goes into the tally, `limit` shapes what comes out.
  5. `vector_store.get_by_ids(top_chunk_ids)` → real `Chunk` text.
  - **Known ranking nuance (not yet fixed, no confirmed bug):** every anchor's votes count equally regardless of its similarity score, so a chunk connected to several low-confidence anchors could in principle outrank a chunk connected to one high-confidence anchor. Considered fix: weight each vote by `anchor["score"]` instead of a flat `+1`. Deferred — traced through a real example (`"Who attends the Cascade Portfolio Summit?"`) expecting this to be the cause of a bad ranking and found the top result was in fact correct (a summary chunk that happened to answer the question); no real failure observed yet, so not implemented speculatively.
- **`query_entity_extractor.py`** (`QueryEntityExtractor`, in `app/extraction/`, not `app/retrieval/`) — **not** an `Extractor` subclass; a separate, narrower interface (`extract(query: str) -> list[Entity]`) built specifically for query-time entity linking. **Why a separate class, not the reused document `Extractor`:** the document extractor's prompt requires every entity to have a description grounded only in the source text (a deliberate, hard-won rule for extraction quality — see Entity Resolution notes above). A bare question like *"Where does Maria Ellison work?"* states no facts about Maria Ellison to ground a description in, so the LLM — correctly following that rule — dropped the entity entirely, and `GraphRetriever` got zero anchors. Confirmed via testing: 2 of 3 test queries returned 0 chunks before this fix. The general lesson (entity linking and relation extraction are normally separate tools in KG-QA systems, not one reused) matches the standard field pattern, not just a local workaround.
  - **`query_entities_response.py`** (`app/extraction/schemas/`) — Pydantic schema with only `name` + `entity_type` (both required; `entity_type` is `Literal[tuple(entity_types)]`, same enum-constraint mechanism as document extraction). No `id`, no `description`, no relationships.
  - **`query_prompt_builder.py`** (`app/extraction/`, sibling to `prompt_builder.py` — not in `schemas/`, which is reserved for Pydantic response models) — lighter prompt, explicitly instructs the model that a bare mention with no stated facts is still a valid entity to extract.
  - `QueryEntityExtractor.extract()` generates a throwaway `uuid4()` for each `Entity.id` (never written to the graph — only exists because the `Entity` dataclass requires an id) and leaves `description=None` (handled gracefully by `build_entity_embedding_text`'s `description or ""`).
- **`hybrid_retriever.py`** (`HybridRetriever`, 2026-07-04) — `HybridRetriever(retrievers: list[Retriever], rrf_k=60, fetch_multiplier=4)`. Fuses any number of `Retriever`s (currently `VectorRetriever` + `GraphRetriever`) via Reciprocal Rank Fusion, not raw score blending — vector cosine-similarity and graph mention-counts aren't on comparable scales, so fusing by rank position sidesteps calibration entirely. `retrieve(query, limit)`:
  1. Over-fetches `limit * fetch_multiplier` from each sub-retriever (rank-position fusion needs a real candidate pool — asking each retriever for exactly `limit` results means most chunks common to both barely overlap, so RRF has nothing to fuse).
  2. For each retriever's ranked list, accumulates `1 / (rrf_k + rank)` per chunk id into a running score, keyed by `chunk.id` (a side dict maps id → `Chunk` since scores are tracked by id, not by object).
  3. Sorts ids by total score descending, takes the top `limit`, returns the corresponding `Chunk`s.
  - Verified end-to-end via `main.py --query` against the real Neo4j + Qdrant graph (Northwind Robotics sample data) — top result matched the query correctly, no errors.
  - **Reranking deliberately skipped for now (2026-07-04)** — decided to build the full query→answer loop end-to-end first (context builder + generation) and only add a reranker later if bad chunks are observed reaching the LLM in practice; RRF's fused ranking was judged good enough to proceed without it.

### Generation (`app/generation/`, 2026-07-04)
- **`context_builder.py`** — `build_context(chunks: list[Chunk]) -> str`. Not an ABC (only one sane way to do this today) — joins chunk texts with a `[Source N]` tag per chunk so the LLM can distinguish/refer to individual sources. No context-window truncation logic yet (not hit in practice with `limit=5` short chunks; revisit if larger `limit`/chunk sizes make it a real constraint).
- **`answer_generator.py`** — `AnswerGenerator` ABC: `generate(query, context) -> str`. Mirrors the `Extractor`/`Retriever` swappable-implementation pattern.
- **`openai_answer_generator.py`** — `OpenAIAnswerGenerator(model="gpt-4o-mini")`. Builds the prompt via `answer_prompt_builder`, calls `chat.completions.create` (plain completion, not structured output — a free-text answer, no schema to constrain), `temperature=0`, returns the raw message content.
- **`answer_prompt_builder.py`** — `build_answer_prompt(query, context) -> str`. Explicitly instructs the model to answer *only* from the given sources and to say so rather than guess if the sources are insufficient — this is what makes the system refuse-to-hallucinate rather than fall back on outside knowledge.
- **Verified end-to-end** via `main.py --query` against the real graph: a grounded question ("Where is Northwind Robotics headquartered?") produced a correct, source-backed answer; two out-of-context questions ("Who is the CFO?", "What color is the Pathfinder 3?") both correctly triggered the "sources do not contain this information" refusal instead of hallucinating.
- **`query_result.py`** — `QueryResult` dataclass: `query`, `answer`, `chunks: list[Chunk]` — the query-side counterpart to `IngestionResult`, returned by `GraphRAGEngine.query()`.

### Engine (`app/engine/`, 2026-07-04)
- **`graph_rag_engine.py`** — `GraphRAGEngine(ingestion_pipeline, retriever, answer_generator, graph_store)`. A thin facade over the three previously-separate flows that `main.py` used to orchestrate inline:
  - `ingest(document_path) -> IngestionResult` — delegates straight to `IngestionPipeline.ingest`.
  - `query(query, limit=5) -> QueryResult` — `retriever.retrieve()` → `build_context()` → `answer_generator.generate()`, packaged into a `QueryResult`.
  - `clear() -> None` — delegates to `graph_store.clear()`.
  - Takes a `Retriever` (not a concrete `HybridRetriever`), an `AnswerGenerator` (not a concrete `OpenAIAnswerGenerator`), and an `IngestionPipeline`/`GraphStore` — same swappable-ABC pattern as the rest of the codebase; the engine doesn't know or care which concrete implementations it was handed.
  - Deliberately holds no config/model-name knowledge itself — all wiring (which retrievers, which model, `CANDIDATE_K`, etc.) stays in the composition root (`main.py`'s `build_engine()`), keeping the engine a pure orchestrator.

### Entry Point
- **`main.py`** — **the composition root** (no longer a disconnected harness). **Refactored 2026-07-04**: all component wiring extracted into `build_engine(config, schema) -> GraphRAGEngine`; `main()` is now a thin CLI that parses args and calls `engine.clear()` / `engine.query()` / `engine.ingest()`. Usage:
  - `python main.py [path/to/doc.pdf] [--clear]` — ingest a document (`--clear` wipes the Neo4j graph first via `engine.clear()`). `build_engine()` wires `DoclingParser`/`DoclingChunker`/`OllamaEmbedder`/`OpenAIExtractor(gpt-4o)`/`QdrantVectorStore`/`Neo4jGraphStore` (computes `embedding_dimensions` from a real probe embedding) + `OpenAIEntityMatcher(gpt-4o)` + `EntityResolver` + `IngestionPipeline`; `main()` prints the returned `IngestionResult` receipt.
  - `python main.py --query "question" [--clear]` — query the graph instead of ingesting. `build_engine()` also wires `QueryEntityExtractor(gpt-4o-mini)` + `VectorRetriever` + `GraphRetriever` (reusing the same `CANDIDATE_K` constant as `EntityResolver`) wrapped in a `HybridRetriever`, plus `OpenAIAnswerGenerator(gpt-4o-mini)`; `main()` calls `engine.query()` and prints the retrieved chunks + final grounded answer from the returned `QueryResult`. Full query→answer loop verified end-to-end against the real graph after the refactor.
  - Both modes load `.env` and share one `GraphRAGEngine` instance (built once per process) rather than constructing components ad hoc per branch.

---

## Not Started

Placeholder directories exist for all of these (empty, no code yet):

- **`app/retrieval/`** — `Retriever` ABC + `VectorRetriever` + `GraphRetriever` + `HybridRetriever` (RRF) **done**
- **`app/reranking/`** — cross-encoder or LLM-based reranker
- **`app/generation/`** — answer generation via LLM
- **`app/utils/`** — shared utilities
- **`app/database/`** — unclear purpose yet; empty

---

## Known Issues / Where to Pick Up

1. ~~`tests/test_ollama_extractor.py` broken constructor call~~ — **fixed 2026-07-03**: now loads `AppConfig`/`GraphSchema` and calls `OllamaExtractor(config=config.ollama, schema=schema)`.
2. No test yet for `Neo4jGraphStore` in isolation (covered indirectly via `test_ingestion_pipeline.py`'s `graph_store` fixture now). Per current testing priorities, not being actively added — see Testing section.
3. ~~No shared `IngestionPipeline` abstraction~~ — **done 2026-07-03**, see Completed above.
4. `StructuredDoclingDocument(Document)` uses inheritance, but violates LSP in practice: `DoclingChunker.chunk()` requires `docling_doc` to be non-null, so a plain `Document` (e.g. from `PDFParser`) can't safely be passed through the `Chunker` interface polymorphically — it'll raise `ValueError`. Not a bug today since `DoclingParser` output is always paired with `DoclingChunker`, but revisit (e.g. composition instead of inheritance, or a narrower interface) if the pipeline ever needs to pick a chunker generically at runtime rather than by construction.
5. `test_ollama_extractor.py` is flaky against small models: on a 2026-07-03 run, `qwen2.5:3b` failed to extract a `Microsoft` entity from a chunk describing "Microsoft invested billions of dollars into OpenAI" — plausibly because "invested" doesn't map cleanly onto any of the schema's allowed relationship types (`WORKS_AT`/`LOCATED_IN`/`CREATED`/`OWNS`), so the model may drop the entity rather than force an ill-fitting relationship. Not addressed yet (candidates: add an `INVESTED_IN` relationship type, or accept some entity-recall variance from a 3B model).
6. `Neo4jGraphStore.add()` isn't transactional per chunk — see note under Knowledge Graph above. If a relationship partway through a chunk's list fails validation, earlier entities/relationships for that chunk are already committed even though `IngestionPipeline` records the whole chunk as failed in `IngestionResult.failures`.
7. ~~**Entity resolution — Phase 2**~~ — **done 2026-07-03**, see "Entity Resolution — Implemented" above. Validated end-to-end across two docs (sample_graphrag_document.pdf and sample_graphrag_document_2.pdf) — clean deduplication, no false merges, type-valid relationships.
8. **Remaining resolution limitations (not bugs, inherent):**
   - **Recall wobble** — extraction is run-to-run non-deterministic at the margins; a true edge or entity can be missed on a given pass (e.g. an orphan node, or a `WORKS_AT` not emitted). Precision is solid; recall varies.
   - **Extraction-reasoning limits** — occasional subject misrouting the endpoint validator can't catch (right entities, wrong wiring); unnamed entities ("a startup in Austin") can't be nodes so their facts drop.
   - **No offline dedup** — resolution is online (resolve-on-ingest); it never compares two *existing* graph nodes to each other, so a duplicate that slips through once persists. A future "collective ER" pass could catch these.
9. **`main.py` runs on `gpt-4o` for both extractor and matcher.** For cheaper runs, switch both `model=` strings to `gpt-4o-mini` (very good; the one thing it misses is hard org-abbreviation merges). Cost is trivial either way (~$0.01/run mini, ~$0.12/run 4o). A good hybrid is mini-extractor + 4o-matcher.

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
| `pydantic` | Structured-output validation (Ollama + OpenAI extraction/matching) |
| `pyyaml` | Config + schema loading |
| `openai` | Production extractor + entity matcher (`gpt-4o` / `gpt-4o-mini`) |
| `python-dotenv` | Loads `OPENAI_API_KEY` from `.env` |

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
- `main.py` is now the wired composition root (`python main.py [doc.pdf] [--clear]`), not just a harness.
- Extraction/matching moved from the local 3B (`qwen2.5:3b`) to OpenAI `gpt-4o`; the Ollama implementations remain as swappable fallbacks behind the same ABCs.
- Entity resolution + relationship-quality work is merged to `main`. An exploratory **schema-induction** feature (k-means-from-scratch diversity sampling to auto-induce the schema) lives on the `feature/schema-induction` branch, unwired — deferred to a future version; `graph.yaml` remains the hand-curated source of truth.

---

## Roadmap (from HANDOFF.md)

1. ~~**IngestionPipeline**~~ — **done 2026-07-03**
2. ~~Integration tests~~ — deferred; building end-to-end first (see Testing note above)
3. ~~**Entity resolution**~~ — **done 2026-07-03** (Phase 1 + Phase 2 + relationship-quality: enriched schema, endpoint validation, OpenAI extraction/matching)
4. ~~Vector retriever~~ — **done** (`app/retrieval/`: `Retriever` ABC + `VectorRetriever`; verified end-to-end against Qdrant)
5. ~~Graph retriever~~ — **done 2026-07-04** (`GraphRetriever` + `QueryEntityExtractor`; entity-anchored 1-hop traversal; verified end-to-end against Neo4j via `main.py --query`)
6. ~~Hybrid retrieval~~ — **done 2026-07-04** (`HybridRetriever`, fuses `VectorRetriever` + `GraphRetriever`)
7. ~~RRF~~ — **done 2026-07-04** (reciprocal rank fusion, `rrf_k=60`, `fetch_multiplier=4`; see `HybridRetriever` above)
8. Reranker — **deferred 2026-07-04**, revisit only if bad chunks are observed reaching the LLM in practice
9. ~~Context builder~~ — **done 2026-07-04** (`build_context`)
10. ~~Answer generation~~ — **done 2026-07-04** (`AnswerGenerator` ABC + `OpenAIAnswerGenerator`; full query→answer loop verified end-to-end via `main.py --query`, including correct refusal on out-of-context questions)
11. ~~GraphRAGEngine~~ — **done 2026-07-04** (`GraphRAGEngine` facade; `main.py` refactored into a thin CLI over it — see `app/engine/` above)
