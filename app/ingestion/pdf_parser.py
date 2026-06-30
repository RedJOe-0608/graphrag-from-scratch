from pathlib import Path
import uuid

import fitz

from app.ingestion.parser import Parser
from app.models.document import Document


class PDFParser(Parser):
    def parse(self, path: str) -> Document:
        pages = []

        with fitz.open(path) as pdf:
            for page in pdf:
                page_text = page.get_text()

                if page_text:
                    pages.append(page_text)

        text = "\n".join(pages)

        return Document(
            id=str(uuid.uuid4()),
            title=Path(path).stem,
            text=text,
        )