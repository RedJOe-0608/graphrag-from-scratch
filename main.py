import sys

from app.chunking.docling_chunker import DoclingChunker
from app.config.app_config_loader import load_app_config
from app.config.graph_schema_loader import load_graph_schema
from app.embeddings.ollama_embedder import OllamaEmbedder
from app.extraction.openai_extractor import OpenAIExtractor
from app.extraction.query_entity_extractor import QueryEntityExtractor
from app.graph_store.neo4j_graph_store import Neo4jGraphStore
from app.ingestion.ingestion_pipeline import IngestionPipeline
from app.parsing.docling_parser import DoclingParser
from app.resolution.entity_resolver import EntityResolver
from app.resolution.ollama_entity_matcher import OllamaEntityMatcher
from app.resolution.openai_entity_matcher import OpenAIEntityMatcher
from app.generation.context_builder import build_context
from app.generation.openai_answer_generator import OpenAIAnswerGenerator
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.hybrid_retriever import HybridRetriever
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

DEFAULT_DOCUMENT = "tests/data/sample_graphrag_document.pdf"


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

    embedder = OllamaEmbedder()
    vector_store = QdrantVectorStore(config=config.qdrant)

    # Derive the embedding dimensionality from a real embedding call rather than
    # hardcoding it — the graph store's vector index needs this at construction.
    embedding_dimensions = len(embedder.embed_text(["probe"])[0])

    graph_store = Neo4jGraphStore(
        config=config.neo4j,
        schema=schema,
        embedding_dimensions=embedding_dimensions,
    )

    if should_clear:
        graph_store.clear()
        print("Cleared existing graph.\n")

    if query:
        query_extractor = QueryEntityExtractor(schema=schema, model="gpt-4o-mini")
        vector_retriever = VectorRetriever(
            vector_store=vector_store,
            embedder=embedder,
        )
        graph_retriever = GraphRetriever(
            graph_store=graph_store,
            vector_store=vector_store,
            embedder=embedder,
            query_extractor=query_extractor,
            k=CANDIDATE_K,
        )
        retriever = HybridRetriever(
            retrievers=[vector_retriever, graph_retriever],
        )

        chunks = retriever.retrieve(query)

        print(f"\nQuery: {query}")
        print(f"Retrieved {len(chunks)} chunk(s):\n")
        for chunk in chunks:
            print(f"[{chunk.id}]\n{chunk.text}\n")

        context = build_context(chunks)
        generator = OpenAIAnswerGenerator(model="gpt-4o-mini")
        answer = generator.generate(query, context)

        print(f"Answer:\n{answer}\n")

        return

    parser = DoclingParser()
    chunker = DoclingChunker()
    extractor = OpenAIExtractor(schema=schema, model="gpt-4o")

    matcher = OpenAIEntityMatcher(model="gpt-4o")
    resolver = EntityResolver(
        graph_store=graph_store,
        embedder=embedder,
        matcher=matcher,
        low_threshold=LOW_THRESHOLD,
        k=CANDIDATE_K,
    )

    pipeline = IngestionPipeline(
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        extractor=extractor,
        vector_store=vector_store,
        resolver=resolver,
    )

    result = pipeline.ingest(document_path)

    print(f"\nDocument:      {result.document.title}")
    print(f"Chunks:        {result.chunk_count}")
    print(f"Entities:      {result.entity_count}")
    print(f"Relationships: {result.relationship_count}")
    print(f"Failures:      {len(result.failures)}")
    for failure in result.failures:
        print(f"  - {failure}")


if __name__ == "__main__":
    main()
