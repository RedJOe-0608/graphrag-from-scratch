from abc import ABC, abstractmethod

from app.models.chunk import Chunk
from app.graph.extracted_knowledge import ExtractedKnowledge


class Extractor(ABC):

    @abstractmethod
    def extract(self, chunk: Chunk) -> ExtractedKnowledge:
        """
        Extract entities and relationships from a chunk.
        """
        pass