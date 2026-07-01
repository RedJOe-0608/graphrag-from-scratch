from dataclasses import dataclass

@dataclass
class Entity:
    id: str
    name: str
    entity_type: str
    description: str | None = None