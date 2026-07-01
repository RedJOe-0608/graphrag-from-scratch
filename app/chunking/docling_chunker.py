import uuid

from docling.chunking import HybridChunker
from transformers import AutoTokenizer

from app.chunking.chunker import Chunker
from app.models.chunk import Chunk
from app.models.structured_docling_document import StructuredDoclingDocument


class DoclingChunker(Chunker):
    def __init__(
        self,
        tokenizer_name: str = "nomic-ai/nomic-embed-text-v1",
        max_tokens: int = 512,
    ):
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        self._chunker = HybridChunker(tokenizer=tokenizer, max_tokens=max_tokens)

    def chunk(self, document: StructuredDoclingDocument) -> list[Chunk]:
        if not document.docling_doc:
            raise ValueError("DoclingChunker requires a StructuredDoclingDocument.")

        return [
            Chunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                text=chunk.text,
            )
            for chunk in self._chunker.chunk(document.docling_doc)
            if chunk.text.strip()
        ]
