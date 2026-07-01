from abc import ABC, abstractmethod

from app.models.embedded_chunk import EmbeddedChunk


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[EmbeddedChunk]) -> None:
        """
        Store embedded chunks.
        """
        pass

    @abstractmethod
    def search(self, query_embedding: list[float],limit: int = 5) -> list[EmbeddedChunk]:
        """
        return the most similar embedded chunks.
        """