from abc import ABC, abstractmethod

from app.graph.extracted_knowledge import ExtractedKnowledge


class GraphStore(ABC):
    @abstractmethod
    def add(self, knowledge: ExtractedKnowledge) -> None:
        """
        Store extracted knowledge in the graph.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all nodes and relationships.
        """
        pass