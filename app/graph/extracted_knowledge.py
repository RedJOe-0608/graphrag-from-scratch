from dataclasses import dataclass

from app.graph.entity import Entity
from app.graph.relationship import Relationship
from app.models.chunk import Chunk

# From a chunk, we extract entities and relationships it contains. this is all it is. 

@dataclass
class ExtractedKnowledge:
    source_chunk: Chunk
    entities: list[Entity]
    relationships: list[Relationship]