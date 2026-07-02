from app.chunking.chunker import Chunker
from app.embeddings.embedder import Embedder
from app.extraction.extractor import Extractor
from app.graph_store.graph_store import GraphStore
from app.ingestion.ingestion_result import IngestionResult
from app.parsing.parser import Parser
from app.vector_store.vector_store import VectorStore

# this pipeline is a thin orchestrator. It only knows the order in which to call.
class IngestionPipeline:
    def __init__(
        self,
        parser: Parser,
        chunker: Chunker,
        embedder: Embedder,
        extractor: Extractor,
        vector_store: VectorStore,
        graph_store: GraphStore,
    ):
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.extractor = extractor
        self.vector_store = vector_store
        self.graph_store = graph_store

    def ingest(self, path: str) -> IngestionResult:
        raise NotImplementedError
