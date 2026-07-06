from dataclasses import dataclass, field

from app.graph.graph_fact import GraphFact
from app.models.chunk import Chunk


@dataclass
class QueryResult:
    query: str
    answer: str
    chunks: list[Chunk] = field(default_factory=list)
    facts: list[GraphFact] = field(default_factory=list)
