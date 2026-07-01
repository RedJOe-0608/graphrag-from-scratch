from app.config.graph_schema import GraphSchema
from app.extraction.extractor import Extractor
from app.models.chunk import Chunk


class OllamaExtractor(Extractor):
    def __init__(self,schema: GraphSchema) -> None:
        self.schema = schema # Schema is part of the extractor's configuration. Once you create an extractor for a particular domain, it shouldn't change schema on a per-chunk basis.
        
    def extract(self, chunk: Chunk):
        raise NotImplementedError