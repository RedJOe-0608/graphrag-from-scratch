from dataclasses import dataclass

@dataclass
class Chunk:
    id=str
    document_id=str
    text=str