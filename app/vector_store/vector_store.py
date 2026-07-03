from abc import ABC, abstractmethod

from app.models.chunk import Chunk
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
        pass

    @abstractmethod
    def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        """
        Return the chunks matching the given ids.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all stored chunks.
        """
        pass
