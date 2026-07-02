from dataclasses import dataclass, field

from app.models.document import Document

# this is the final receipt, returned to us after the entire pipeline is done
@dataclass
class IngestionResult:
    document: Document
    chunk_count: int
    entity_count: int
    relationship_count: int
    failures: list[str] = field(default_factory=list)