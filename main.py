import sys

from app.chunking.docling_chunker import DoclingChunker
from app.config.app_config_loader import load_app_config
from app.config.graph_schema_loader import load_graph_schema
from app.embeddings.ollama_embedder import OllamaEmbedder
from app.extraction.openai_extractor import OpenAIExtractor
from app.graph_store.neo4j_graph_store import Neo4jGraphStore
from app.ingestion.ingestion_pipeline import IngestionPipeline
from app.parsing.docling_parser import DoclingParser
from app.resolution.entity_resolver import EntityResolver
from app.resolution.ollama_entity_matcher import OllamaEntityMatcher
from app.resolution.openai_entity_matcher import OpenAIEntityMatcher
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
    # Usage: python main.py [path/to/doc.pdf] [--clear]
    #   path defaults to the sample doc; --clear wipes the graph before ingesting.
    #   Omit --clear to ingest ON TOP of the existing graph (cross-document resolution).
    args = [a for a in sys.argv[1:] if a != "--clear"]
    document_path = args[0] if args else DEFAULT_DOCUMENT
    should_clear = "--clear" in sys.argv

    config = load_app_config("config/app.yaml")
    schema = load_graph_schema("config/graph.yaml")

    parser = DoclingParser()
    chunker = DoclingChunker()
    embedder = OllamaEmbedder()
    extractor = OpenAIExtractor(schema=schema, model="gpt-4o")
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
