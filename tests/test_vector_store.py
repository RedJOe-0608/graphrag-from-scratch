import uuid
from app.chunking.sentence_chunker import SentenceChunker
from app.embeddings.ollama_embedder import OllamaEmbedder
from app.ingestion.pdf_parser import PDFParser
from app.models.chunk import Chunk
from app.models.embedded_chunk import EmbeddedChunk


def test_qdrant_vector_store_returns_relevant_chunks(vector_store):
    parser = PDFParser()
    chunker = SentenceChunker()
    embedder = OllamaEmbedder()

    document = parser.parse("tests/data/sample_graphrag_document.pdf")
    chunks = chunker.chunk(document)
    embedded_chunks = embedder.embed(chunks)
    vector_store.add(embedded_chunks)

    assert vector_store.client.collection_exists(vector_store.collection_name)

    query_chunk = Chunk(
        id=str(uuid.uuid4()),
        document_id=document.id,
        text="What is the main topic of the document?",
    )
    query_embedding = embedder.embed([query_chunk])
    results = vector_store.search(query_embedding[0].embedding)

    assert len(results) > 0
    assert len(results) <= 5

    for result in results:
        assert isinstance(result, EmbeddedChunk)
        assert isinstance(result.chunk.text, str) and result.chunk.text
        assert isinstance(result.embedding, list) and len(result.embedding) > 0


def test_qdrant_vector_store_add_empty_list(vector_store):
    vector_store.add([])
    assert not vector_store.client.collection_exists(vector_store.collection_name)
