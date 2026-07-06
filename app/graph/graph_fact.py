from dataclasses import dataclass


@dataclass(frozen=True)
class GraphFact:
    """
    A single relationship from the knowledge graph, oriented for reading:
    `source --relationship_type--> target`. Frozen so facts can be deduplicated
    in a set. The description, when present, is the edge's own explanation.
    """

    source: str
    relationship_type: str
    target: str
    description: str | None = None
