from app.ingestion.pdf_parser import PDFParser
from app.chunking.sentence_chunker import SentenceChunker
from app.embeddings.ollama_embedder import OllamaEmbedder
from app.vector_store.qdrant_vector_store import QdrantVectorStore

def test_ingestion_pipeline():
    parser = PDFParser()
    chunker = SentenceChunker()
    embedder = OllamaEmbedder()
    vector_store = QdrantVectorStore(collection_name="test_collection")

    # Delete collection if it exists
    if vector_store.client.collection_exists(vector_store.collection_name):
        vector_store.client.delete_collection(vector_store.collection_name)

    document = parser.parse("tests/data/sample_graphrag_document.pdf")
    chunks = chunker.chunk(document)

    assert len(chunks) > 0

    embedded_chunks = embedder.embed(chunks)

    assert len(chunks) == len(embedded_chunks)

    vector_store.add(embedded_chunks)

    count = vector_store.client.count(collection_name=vector_store.collection_name)

    assert count.count == len(embedded_chunks)