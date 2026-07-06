from abc import ABC, abstractmethod

from app.models.chunk import Chunk


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: list[Chunk], limit: int = 5) -> list[Chunk]:
        """
        Reorder chunks by relevance to the query, returning the top `limit`,
        most relevant first.
        """
        pass
