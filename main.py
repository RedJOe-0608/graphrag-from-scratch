from app.chunking.sentence_chunker import SentenceChunker
from app.embeddings.ollama_embedder import OllamaEmbedder
from app.ingestion.pdf_parser import PDFParser
from app.models.document import Document

def main():
    parser = PDFParser()
    chunker = SentenceChunker()
    embedder = OllamaEmbedder()

    # document = parser.parse("data/sample.pdf")

    # chunks = chunker.chunk(document)

    # print(f"Created {len(chunks)} chunks\n")

    # embdedded_chunks = embedder.embed(chunks=chunks)

    # first_embdedded_chunk = embdedded_chunks[0]
    # print(first_embdedded_chunk.chunk.text)
    # print(first_embdedded_chunk.embedding)


if __name__ == "__main__":
    main()