import sys

from app.chunking.docling_chunker import DoclingChunker
from app.config.app_config_loader import load_app_config
from app.config.graph_schema_loader import load_graph_schema
from app.embeddings.ollama_embedder import OllamaEmbedder
from app.engine.graph_rag_engine import GraphRAGEngine
from app.extraction.openai_extractor import OpenAIExtractor
from app.extraction.query_entity_extractor import QueryEntityExtractor
from app.generation.openai_answer_generator import OpenAIAnswerGenerator
from app.graph_store.neo4j_graph_store import Neo4jGraphStore
from app.ingestion.ingestion_pipeline import IngestionPipeline
from app.keyword_store.bm25_keyword_store import BM25KeywordStore
from app.parsing.docling_parser import DoclingParser
from app.reranking.cross_encoder_reranker import CrossEncoderReranker
from app.resolution.entity_resolver import EntityResolver
from app.resolution.openai_entity_matcher import OpenAIEntityMatcher
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.graph_traversal import GraphTraversal
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.keyword_retriever import KeywordRetriever
from app.retrieval.reranking_retriever import RerankingRetriever
from app.retrieval.vector_retriever import VectorRetriever
from app.vector_store.qdrant_vector_store import QdrantVectorStore

from dotenv import load_dotenv

# Entity resolution: candidates scoring below LOW_THRESHOLD are not plausible
# and are filtered out before the LLM. Everything at/above it (top-K) is handed
# to the LLM matcher, which picks the same-entity candidate or "none". There is
# no HIGH auto-merge band — observed true/false-merge scores overlap, so no
# threshold can safely auto-merge; the LLM is the sole arbiter.
LOW_THRESHOLD = 0.75
CANDIDATE_K = 5

# Upper bound on relationship facts fed to the LLM per query, so a highly
# connected entity can't swamp the prompt.
MAX_GRAPH_FACTS = 20

DEFAULT_DOCUMENT = "tests/data/sample_graphrag_document.pdf"


def build_engine(config, schema) -> GraphRAGEngine:
    embedder = OllamaEmbedder()
    vector_store = QdrantVectorStore(config=config.qdrant)
    keyword_store = BM25KeywordStore(config=config.keyword)

    # Derive the embedding dimensionality from a real embedding call rather than
    # hardcoding it — the graph store's vector index needs this at construction.
    embedding_dimensions = len(embedder.embed_text(["probe"])[0])

    graph_store = Neo4jGraphStore(
        config=config.neo4j,
        schema=schema,
        embedding_dimensions=embedding_dimensions,
    )

    parser = DoclingParser()
    chunker = DoclingChunker()
    extractor = OpenAIExtractor(schema=schema, model="gpt-4o-mini")

    matcher = OpenAIEntityMatcher(model="gpt-4o-mini")
    resolver = EntityResolver(
        graph_store=graph_store,
        embedder=embedder,
        matcher=matcher,
        low_threshold=LOW_THRESHOLD,
        k=CANDIDATE_K,
    )

    ingestion_pipeline = IngestionPipeline(
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        extractor=extractor,
        vector_store=vector_store,
        keyword_store=keyword_store,
        resolver=resolver,
    )

    query_extractor = QueryEntityExtractor(schema=schema, model="gpt-4o-mini")
    vector_retriever = VectorRetriever(
        vector_store=vector_store,
        embedder=embedder,
    )
    keyword_retriever = KeywordRetriever(keyword_store=keyword_store)

    # One graph walk feeds two consumers: the GraphRetriever below (chunks, into
    # RRF) and the engine (relationship facts, into the LLM context).
    graph_traversal = GraphTraversal(
        graph_store=graph_store,
        embedder=embedder,
        query_extractor=query_extractor,
        k=CANDIDATE_K,
        max_facts=MAX_GRAPH_FACTS,
    )
    graph_retriever = GraphRetriever(
        traversal=graph_traversal,
        vector_store=vector_store,
    )
    hybrid_retriever = HybridRetriever(
        retrievers=[vector_retriever, keyword_retriever, graph_retriever],
    )

    # RRF fusion is cheap, so we keep it as the first stage: it fuses the three
    # retrievers' results into a broad candidate pool, which the cross-encoder
    # reranker then rescores to pick the final chunks.
    reranker = CrossEncoderReranker(model=config.reranker.model)
    retriever = RerankingRetriever(
        retriever=hybrid_retriever,
        reranker=reranker,
        candidate_pool=config.reranker.candidate_pool,
    )

    answer_generator = OpenAIAnswerGenerator(model="gpt-4o-mini")

    return GraphRAGEngine(
        ingestion_pipeline=ingestion_pipeline,
        retriever=retriever,
        answer_generator=answer_generator,
        graph_store=graph_store,
        vector_store=vector_store,
        keyword_store=keyword_store,
        graph_traversal=graph_traversal,
    )


def main():

    load_dotenv()
    # Usage:
    #   python main.py [path/to/doc.pdf] [--clear]      ingest a document
    #   python main.py --query "question" [--clear]     query the graph
    #   path defaults to the sample doc; --clear wipes the graph first.
    #   Omit --clear to ingest ON TOP of the existing graph (cross-document resolution).
    raw_args = sys.argv[1:]
    should_clear = "--clear" in raw_args

    query = None
    if "--query" in raw_args:
        query = raw_args[raw_args.index("--query") + 1]

    positional = [
        a for a in raw_args if a not in ("--clear", "--query", query)
    ]
    document_path = positional[0] if positional else DEFAULT_DOCUMENT

    config = load_app_config("config/app.yaml")
    schema = load_graph_schema("config/graph.yaml")

    engine = build_engine(config, schema)

    if should_clear:
        engine.clear()
        print("Cleared existing graph.\n")

    if query:
        result = engine.query(query)

        print(f"\nQuery: {result.query}")
        print(f"Retrieved {len(result.chunks)} chunk(s):\n")
        for chunk in result.chunks:
            print(f"[{chunk.id}]\n{chunk.text}\n")

        if result.facts:
            print(f"Graph facts ({len(result.facts)}):")
            for fact in result.facts:
                line = f"  {fact.source} --{fact.relationship_type}--> {fact.target}"
                if fact.description:
                    line += f" ({fact.description})"
                print(line)
            print()

        print(f"Answer:\n{result.answer}\n")

        return

    result = engine.ingest(document_path)

    print(f"\nDocument:      {result.document.title}")
    print(f"Chunks:        {result.chunk_count}")
    print(f"Entities:      {result.entity_count}")
    print(f"Relationships: {result.relationship_count}")
    print(f"Failures:      {len(result.failures)}")
    for failure in result.failures:
        print(f"  - {failure}")


if __name__ == "__main__":
    main()
