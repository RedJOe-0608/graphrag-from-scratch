from app.ingestion.pdf_parser import PDFParser
from app.models.document import Document

def main():
    parser = PDFParser()

    document = parser.parse("data/sample.pdf")

    print("=" * 50)
    print(f"ID: {document.id}")
    print(f"Title: {document.title}")
    print("=" * 50)
    print(document.text[:1000])


if __name__ == "__main__":
    main()