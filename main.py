from app.chunking.docling_chunker import DoclingChunker
from app.chunking.sentence_chunker import SentenceChunker
from app.config.schema_loader import load_graph_schema
from app.embeddings.ollama_embedder import OllamaEmbedder
from app.ingestion.docling_parser import DoclingParser
from app.ingestion.pdf_parser import PDFParser
from app.models.document import Document

def main():
    parser = DoclingParser()
    chunker = DoclingChunker()
    embedder = OllamaEmbedder()

    # document = parser.parse("tests/data/sample_graphrag_document.pdf")

    schema = load_graph_schema("config/graph.yaml")

    print(schema)

    # chunks = chunker.chunk(document)

    # print(f"Created {len(chunks)} chunks\n")

    # embdedded_chunks = embedder.embed(chunks=chunks)

    # first_embdedded_chunk = embdedded_chunks[0]
    # print(first_embdedded_chunk.chunk.text)
    # print(first_embdedded_chunk.embedding)


if __name__ == "__main__":
    main()