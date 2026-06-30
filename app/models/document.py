from dataclasses import dataclass

@dataclass
class Document:
    id: str
    title: str
    text: str