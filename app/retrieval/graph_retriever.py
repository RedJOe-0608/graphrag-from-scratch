from app.models.chunk import Chunk
from app.retrieval.graph_traversal import GraphTraversal
from app.retrieval.retriever import Retriever
from app.vector_store.vector_store import VectorStore


class GraphRetriever(Retriever):
    """
    The chunk-facing view of the graph walk: ranks chunks by how often the
    query's entities reach them, then fetches their text. The walk itself lives
    in GraphTraversal, shared with the engine's fact channel so it runs once.
    """

    def __init__(
        self,
        traversal: GraphTraversal,
        vector_store: VectorStore,
    ) -> None:
        self.traversal = traversal
        self.vector_store = vector_store

    def retrieve(self, query: str, limit: int = 5) -> list[Chunk]:
        chunk_id_counts = self.traversal.traverse(query).chunk_id_counts

        if not chunk_id_counts:
            return []

        top_chunk_ids = [
            chunk_id for chunk_id, _ in chunk_id_counts.most_common(limit)
        ]

        return self.vector_store.get_by_ids(top_chunk_ids)
