from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: str
    name: str
    entity_type: str
    description: str | None = None