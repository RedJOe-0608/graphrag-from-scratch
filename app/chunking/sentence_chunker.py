import uuid
from app.chunking.chunker import Chunker
from app.models.chunk import Chunk
from app.models.document import Document


class SentenceChunker(Chunker):
    def chunk(self, document: Document) -> list[Chunk]:
        sentences = document.text.split(".")

        chunks = []

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    document_id=document.id,
                    text=sentence
                )
            )

        return chunks