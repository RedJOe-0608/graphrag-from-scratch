from abc import ABC, abstractmethod

from app.models.chunk import Chunk


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, limit: int = 5) -> list[Chunk]:
        """
        Return the most relevant chunks for a query, most relevant first.
        """
        pass
