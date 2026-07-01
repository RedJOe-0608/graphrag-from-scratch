from app.graph.entity import Entity
from app.graph.relationship import Relationship
from app.graph.extracted_knowledge import ExtractedKnowledge
from app.models.chunk import Chunk

from app.extraction.schemas.extracted_knowledge_response import (
    ExtractedKnowledgeResponse,
)


def to_extracted_knowledge(
    chunk: Chunk,
    response: ExtractedKnowledgeResponse,
) -> ExtractedKnowledge:

    entities = [
        Entity(
            id=entity.id,
            name=entity.name,
            entity_type=entity.entity_type,
            description=entity.description,
        )
        for entity in response.entities
    ]

    relationships = [
        Relationship(
            source=relationship.source,
            target=relationship.target,
            relationship_type=relationship.relationship_type,
            description=relationship.description,
        )
        for relationship in response.relationships
    ]

    return ExtractedKnowledge(
        chunk_id=chunk.id,
        entities=entities,
        relationships=relationships,
    )