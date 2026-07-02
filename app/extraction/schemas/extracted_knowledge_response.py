from pydantic import BaseModel, create_model

from app.config.graph_schema import GraphSchema
from app.extraction.schemas.entity_response import build_entity_response
from app.extraction.schemas.relationship_response import build_relationship_response


def build_extracted_knowledge_response(schema: GraphSchema) -> type[BaseModel]:
    entity_response = build_entity_response(schema.entity_types)
    relationship_response = build_relationship_response(schema.relationship_types)

    return create_model(
        "ExtractedKnowledgeResponse",
        entities=(list[entity_response], ...),
        relationships=(list[relationship_response], ...),
    )
