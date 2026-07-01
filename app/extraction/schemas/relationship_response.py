from pydantic import BaseModel


class RelationshipResponse(BaseModel):
    source: str
    target: str
    relationship_type: str
    description: str | None = None