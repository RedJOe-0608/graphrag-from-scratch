from typing import Literal

from pydantic import BaseModel, create_model


def build_entity_response(entity_types: list[str]) -> type[BaseModel]:
    return create_model(
        "EntityResponse",
        id=(str, ...),
        name=(str, ...),
        entity_type=(Literal[tuple(entity_types)], ...),
        description=(str, ...),
    )
