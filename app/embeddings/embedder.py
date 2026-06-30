from abc import ABC, abstractmethod

from app.models.chunk import Chunk
from app.models.embedded_chunk import EmbeddedChunk


class Embedder(ABC):
    @abstractmethod
    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        """
        Generate embeddings for a batch of sentences. returns a list of embedding vectors.
        """
        pass