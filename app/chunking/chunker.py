from abc import ABC, abstractmethod

from app.models.chunk import Chunk
from app.models.document import Document


class Chunker(ABC):
    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """
        Convert a document into chunks
        """
        pass