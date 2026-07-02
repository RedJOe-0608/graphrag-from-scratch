from app.parsing.pdf_parser import PDFParser
from app.chunking.sentence_chunker import SentenceChunker
from app.embeddings.ollama_embedder import OllamaEmbedder


def test_ingestion_pipeline(vector_store):
    parser = PDFParser()
    chunker = SentenceChunker()
    embedder = OllamaEmbedder()

    document = parser.parse("tests/data/sample_graphrag_document.pdf")
    assert isinstance(document.id, str) and document.id
    assert isinstance(document.text, str) and document.text

    chunks = chunker.chunk(document)
    assert len(chunks) > 0

    embedded_chunks = embedder.embed(chunks)
    assert len(chunks) == len(embedded_chunks)
    assert len(embedded_chunks[0].embedding) > 0

    vector_store.add(embedded_chunks)

    count = vector_store.client.count(collection_name=vector_store.collection_name)
    assert count.count == len(embedded_chunks)
