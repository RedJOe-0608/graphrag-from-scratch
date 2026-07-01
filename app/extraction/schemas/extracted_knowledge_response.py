from pydantic import BaseModel

from app.extraction.schemas.entity_response import EntityResponse
from app.extraction.schemas.relationship_response import RelationshipResponse


class ExtractedKnowledgeResponse(BaseModel):
    entities: list[EntityResponse]
    relationships: list[RelationshipResponse]