from typing import Literal

from pydantic import BaseModel, create_model


def build_relationship_response(relationship_types: list[str]) -> type[BaseModel]:
    return create_model(
        "RelationshipResponse",
        source=(str, ...),
        target=(str, ...),
        relationship_type=(Literal[tuple(relationship_types)], ...),
        description=(str | None, None),
    )
