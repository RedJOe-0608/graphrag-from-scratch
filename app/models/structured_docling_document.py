from dataclasses import dataclass
from docling.datamodel.document import DoclingDocument
from app.models.document import Document


@dataclass
class StructuredDoclingDocument(Document):
    docling_doc: DoclingDocument = None
