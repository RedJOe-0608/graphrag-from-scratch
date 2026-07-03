# GraphRAG from First Principles

This project is an implementation of a production-inspired GraphRAG system built from scratch.

## Goals

- Understand every component instead of relying on frameworks
- Implement semantic chunking
- Build a knowledge graph with Neo4j
- Store embeddings in Qdrant
- Perform hybrid retrieval
- Implement Reciprocal Rank Fusion
- Add reranking
- Generate answers using local LLMs through Ollama

The project is being built incrementally with each component implemented and explained from first principles.

## Architecture

```
INGESTION:
  PDF ─▶ DoclingParser ─▶ DoclingChunker ─▶ chunks
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼ (Track A: vectors)                 (Track B: graph) ▼
             OllamaEmbedder                          OpenAIExtractor (entities+rels)
                    │                                         │
             QdrantVectorStore                        EntityResolver (dedup via LLM)
             (chunk vectors)                                  │
                                                       Neo4jGraphStore
                                              (entities+relationships, +source_chunk_ids)

QUERY:
  question ─┬─▶ VectorRetriever ─▶ Qdrant ──────┐
            │                                    ├─▶ RRF fusion ─▶ top chunks
            └─▶ GraphRetriever ─▶ Neo4j ─────────┘                   │
                (extract entities → anchors → 1-hop → chunk votes)   │
                                                          build_context ([Source N])
                                                                     │
                                                       OpenAIAnswerGenerator (grounded)
                                                                     │
                                                                  QueryResult
```