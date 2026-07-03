from dataclasses import dataclass


@dataclass
class RelationshipEndpoints:
    source: list[str]
    target: list[str]


@dataclass
class GraphSchema:
    entity_types: list[str]
    # relationship_types holds just the names — kept as a flat list so the
    # extraction enum and the graph store's allowed-set consume it unchanged.
    relationship_types: list[str]
    # relationship_endpoints maps each name to its legal source/target entity
    # types, used to validate relationship endpoints during extraction.
    relationship_endpoints: dict[str, RelationshipEndpoints]
