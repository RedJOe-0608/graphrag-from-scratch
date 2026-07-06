from app.generation.answer_generator import AnswerGenerator
from app.generation.context_builder import build_context
from app.generation.query_result import QueryResult
from app.graph_store.graph_store import GraphStore
from app.ingestion.ingestion_pipeline import IngestionPipeline
from app.ingestion.ingestion_result import IngestionResult
from app.keyword_store.keyword_store import KeywordStore
from app.retrieval.graph_traversal import GraphTraversal
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
        keyword_store: KeywordStore,
        graph_traversal: GraphTraversal | None = None,
    ) -> None:
        self.ingestion_pipeline = ingestion_pipeline
        self.retriever = retriever
        self.answer_generator = answer_generator
        self.graph_store = graph_store
        self.vector_store = vector_store
        self.keyword_store = keyword_store
        # Same traversal the chunk-side GraphRetriever uses; sharing it means the
        # graph walk (and its LLM entity extraction) happens once per query, and
        # we read the relationship facts straight off it for the LLM context.
        self.graph_traversal = graph_traversal

    def ingest(self, document_path: str) -> IngestionResult:
        return self.ingestion_pipeline.ingest(document_path)

    def query(self, query: str, limit: int = 5) -> QueryResult:
        chunks = self.retriever.retrieve(query, limit=limit)

        facts = (
            self.graph_traversal.traverse(query).facts
            if self.graph_traversal is not None
            else []
        )

        context = build_context(chunks, facts)
        answer = self.answer_generator.generate(query, context)

        return QueryResult(query=query, answer=answer, chunks=chunks, facts=facts)

    def clear(self) -> None:
        self.graph_store.clear()
        self.vector_store.clear()
        self.keyword_store.clear()
