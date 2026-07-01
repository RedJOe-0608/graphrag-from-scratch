from dataclasses import dataclass

from app.graph.entity import Entity
from app.graph.relationship import Relationship

# From a chunk, we extract entities and relationships it contains. this is all it is. 

@dataclass
class ExtractedKnowledge:
    chunk_id: str
    entities: list[Entity]
    relationships: list[Relationship]