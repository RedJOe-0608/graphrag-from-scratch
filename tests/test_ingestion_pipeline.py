from app.chunking.docling_chunker import DoclingChunker
from app.embeddings.ollama_embedder import OllamaEmbedder
from app.extraction.ollama_extractor import OllamaExtractor
from app.ingestion.ingestion_pipeline import IngestionPipeline
from app.parsing.docling_parser import DoclingParser


def test_ingestion_pipeline(vector_store, graph_store, app_config, graph_schema):

    pipeline = IngestionPipeline(
        parser=DoclingParser(),
        chunker=DoclingChunker(),
        embedder=OllamaEmbedder(),
        extractor=OllamaExtractor(config=app_config.ollama, schema=graph_schema),
        vector_store=vector_store,
        graph_store=graph_store,
    )

    result = pipeline.ingest("tests/data/sample_graphrag_document.pdf")

    assert result.chunk_count > 0
    assert result.entity_count > 0
    assert all(isinstance(f, str) for f in result.failures)

    vector_count = vector_store.client.count(collection_name=vector_store.collection_name)
    assert vector_count.count == result.chunk_count

