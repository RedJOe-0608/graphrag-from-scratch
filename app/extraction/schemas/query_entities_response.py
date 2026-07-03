from typing import Literal

from pydantic import BaseModel, create_model


def build_query_entities_response(entity_types: list[str]) -> type[BaseModel]:
    entity_mention = create_model(
        "EntityMention",
        name=(str, ...),
        entity_type=(Literal[tuple(entity_types)], ...),
    )

    return create_model(
        "QueryEntitiesResponse",
        entities=(list[entity_mention], ...),
    )
