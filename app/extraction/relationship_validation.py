from pydantic import BaseModel

from app.config.graph_schema import GraphSchema
from app.graph.entity import Entity
from app.graph.relationship import Relationship


def build_valid_relationships(
    validated_response: BaseModel,
    entities: list[Entity],
    schema: GraphSchema,
) -> list[Relationship]:
    """
    Build Relationship objects from the validated extraction response, dropping
    any that are invalid on either count:

    1. Self-consistency — source and target must be entities actually declared
       in this chunk (no dangling references that Neo4j would silently drop).
    2. Endpoint types — the source/target entity types must be legal for the
       relationship type (e.g. WORKS_AT must go Person -> Organization, so a
       WORKS_AT pointing at a Location is dropped rather than written).
    """
    entity_types = {entity.id: entity.entity_type for entity in entities}

    valid = []
    for rel in validated_response.relationships:
        if rel.source not in entity_types or rel.target not in entity_types:
            continue

        endpoints = schema.relationship_endpoints.get(rel.relationship_type)
        if endpoints is not None:
            if entity_types[rel.source] not in endpoints.source:
                continue
            if entity_types[rel.target] not in endpoints.target:
                continue

        valid.append(
            Relationship(
                source=rel.source,
                target=rel.target,
                relationship_type=rel.relationship_type,
                description=rel.description,
            )
        )
    return valid
