from app.chunking.chunker import Chunker
from app.embeddings.embedder import Embedder
from app.extraction.extractor import Extractor
from app.ingestion.ingestion_result import IngestionResult
from app.parsing.parser import Parser
from app.resolution.entity_resolver import EntityResolver
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
        resolver: EntityResolver,
    ):
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.extractor = extractor
        self.vector_store = vector_store
        self.resolver = resolver

    def ingest(self, path: str) -> IngestionResult:
        document = self.parser.parse(path)
        chunks = self.chunker.chunk(document)
        embedded_chunks = self.embedder.embed_chunk(chunks)
        self.vector_store.add(embedded_chunks)

        entity_count = 0
        relationship_count = 0
        failures = []

        for chunk in chunks:
            try:
                knowledge = self.extractor.extract(chunk)
                relationships_written = self.resolver.resolve_knowledge(knowledge)
            except ValueError as e:
                failures.append(f"chunk {chunk.id}: {e}")
                continue

            entity_count += len(knowledge.entities)
            relationship_count += relationships_written

        return IngestionResult(
            document=document,
            chunk_count=len(chunks),
            entity_count=entity_count,
            relationship_count=relationship_count,
            failures=failures,
        )
