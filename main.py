from app.chunking.sentence_chunker import SentenceChunker
from app.ingestion.pdf_parser import PDFParser
from app.models.document import Document

def main():
    parser = PDFParser()
    chunker = SentenceChunker()

    document = parser.parse("data/sample.pdf")

    chunks = chunker.chunk(document)

    print(f"Created {len(chunks)} chunks\n")

    for chunk in chunks[:5]:
        print(chunk)
        print("-" * 50)


if __name__ == "__main__":
    main()