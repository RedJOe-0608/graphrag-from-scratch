from abc import ABC, abstractmethod

from app.models.chunk import Chunk


class KeywordStore(ABC):
    @abstractmethod
    def add(self, chunks: list[Chunk]) -> None:
        """
        Index chunks for keyword search, persisting the index to disk.
        """
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[Chunk]:
        """
        Return the highest BM25-scoring chunks for a query, most relevant first.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Remove the persisted index.
        """
        pass
