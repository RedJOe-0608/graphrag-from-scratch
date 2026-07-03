from abc import ABC, abstractmethod

from app.graph.entity import Entity
from app.graph.extracted_knowledge import ExtractedKnowledge
from app.graph.relationship import Relationship


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

    @abstractmethod
    def find_similar_entities(
        self,
        entity_type: str,
        embedding: list[float],
        k: int = 5,
    ) -> list[dict]:
        """
        Return up to k entities of the given type, ranked by similarity
        to the given embedding.
        """
        pass

    @abstractmethod
    def upsert_entity(self, entity: Entity) -> None:
        """
        Create or update a single entity, keyed by its id.
        """
        pass

    @abstractmethod
    def add_relationship(self, relationship: Relationship) -> None:
        """
        Create or update a single relationship between two existing entities.
        """
        pass

    @abstractmethod
    def get_relationships(self, entity_id: str) -> list[dict]:
        """
        Return the relationships connected to this entity, each as
        {"direction": "out"|"in", "type": <rel_type>, "other_name": <neighbor name>}.
        """
        pass

