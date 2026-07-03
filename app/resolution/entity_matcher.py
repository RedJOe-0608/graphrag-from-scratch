from abc import ABC, abstractmethod

from app.graph.entity import Entity


class EntityMatcher(ABC):
    @abstractmethod
    def match_entity(
        self,
        entity: Entity,
        entity_relationships: list[str],
        source_text: str,
        candidates: list[dict],
        candidate_relationships: dict[str, list[str]],
    ) -> str | None:
        """
        Given a newly extracted entity (with its chunk relationships and source
        text) and a list of candidate graph entities (each with its
        relationships, keyed by id), return the id of the candidate that is the
        SAME real-world entity, or None if none of them match.
        """
        pass
