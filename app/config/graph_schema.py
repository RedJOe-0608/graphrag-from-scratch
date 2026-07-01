from dataclasses import dataclass

@dataclass
class GraphSchema:
    entity_types: list[str]
    relationship_types: list[str]