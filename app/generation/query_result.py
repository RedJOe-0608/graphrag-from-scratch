from dataclasses import dataclass, field

from app.models.chunk import Chunk


@dataclass
class QueryResult:
    query: str
    answer: str
    chunks: list[Chunk] = field(default_factory=list)
