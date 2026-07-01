from dataclasses import dataclass

@dataclass
class Relationship:
    source: str # this is the source entity ID
    target: str # this is the destination entity ID
    relationship_type: str
    description: str | None = None