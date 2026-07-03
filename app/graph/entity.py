from dataclasses import dataclass, field

@dataclass
class Entity:
    id: str
    name: str
    entity_type: str
    description: str | None = None
    aliases: list[str] = field(default_factory=list)
    embedding: list[float] | None = None


def build_entity_embedding_text(entity: Entity) -> str:
    description = entity.description or ""
    return f"{entity.name}. {description}"
 