from pathlib import Path
import uuid

from docling.datamodel.base_models import InputFormat
from app.parsing.parser import Parser
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions

from app.models.structured_docling_document import StructuredDoclingDocument

class DoclingParser(Parser):
    def __init__(self) -> None:
        # convention for a private attribute.
        # DocumentConverter() is expensive to initialise. It loads ML models into memory.
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def parse(self, path: str) -> StructuredDoclingDocument:
        result = self._converter.convert(path)
        text = result.document.export_to_markdown()

        return StructuredDoclingDocument(
            id=str(uuid.uuid4()),
            title=Path(path).stem,
            text=text,
            docling_doc=result.document
        )
