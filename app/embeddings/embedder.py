from abc import ABC, abstractmethod

from app.models.chunk import Chunk
from app.models.embedded_chunk import EmbeddedChunk


class Embedder(ABC):
    @abstractmethod
    def embed_chunk(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        """
        Generate embeddings for a batch of sentences. returns a list of embedding vectors.
        """
        pass

    @abstractmethod
    def embed_text(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for arbitrary text, not tied to a Chunk.
        """
        pass