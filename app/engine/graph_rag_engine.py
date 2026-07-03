from app.generation.answer_generator import AnswerGenerator
from app.generation.context_builder import build_context
from app.generation.query_result import QueryResult
from app.graph_store.graph_store import GraphStore
from app.ingestion.ingestion_pipeline import IngestionPipeline
from app.ingestion.ingestion_result import IngestionResult
from app.retrieval.retriever import Retriever
from app.vector_store.vector_store import VectorStore


class GraphRAGEngine:
    def __init__(
        self,
        ingestion_pipeline: IngestionPipeline,
        retriever: Retriever,
        answer_generator: AnswerGenerator,
        graph_store: GraphStore,
        vector_store: VectorStore,
    ) -> None:
        self.ingestion_pipeline = ingestion_pipeline
        self.retriever = retriever
        self.answer_generator = answer_generator
        self.graph_store = graph_store
        self.vector_store = vector_store

    def ingest(self, document_path: str) -> IngestionResult:
        return self.ingestion_pipeline.ingest(document_path)

    def query(self, query: str, limit: int = 5) -> QueryResult:
        chunks = self.retriever.retrieve(query, limit=limit)
        context = build_context(chunks)
        answer = self.answer_generator.generate(query, context)

        return QueryResult(query=query, answer=answer, chunks=chunks)

    def clear(self) -> None:
        self.graph_store.clear()
        self.vector_store.clear()
