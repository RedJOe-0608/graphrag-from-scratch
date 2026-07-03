from app.embeddings.embedder import Embedder
from app.models.chunk import Chunk
from app.retrieval.retriever import Retriever
from app.vector_store.vector_store import VectorStore


class VectorRetriever(Retriever):
    def __init__(
        self,
        vector_store: VectorStore,
        embedder: Embedder,
    ) -> None:
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, limit: int = 5) -> list[Chunk]:
        query_embedding = self.embedder.embed_text([query])[0]

        embedded_chunks = self.vector_store.search(
            query_embedding=query_embedding,
            limit=limit,
        )

        return [embedded_chunk.chunk for embedded_chunk in embedded_chunks]
