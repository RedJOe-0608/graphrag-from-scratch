from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.models.embedded_chunk import EmbeddedChunk
from app.vector_store.vector_store import VectorStore


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "documents"
    ) -> None:
        self.collection_name = collection_name
        self.client = QdrantClient(
            host=host,
            port=port
        )

    def _create_collection_if_not_exists(self, vector_size: int) -> None:
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

    def add(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        """
        Add a list of embedded chunks to the vector store.
        """

        if not embedded_chunks:
            return

        vector_size = len(embedded_chunks[0].embedding)

        # Lazy collection creation.
        self._create_collection_if_not_exists(vector_size)

        # Convert EmbeddedChunks to PointStructs
        points = [
            PointStruct(
                id=embedded_chunk.chunk.id,
                vector=embedded_chunk.embedding,
                payload={
                    "document_id": embedded_chunk.chunk.document_id,
                    "text": embedded_chunk.chunk.text,
                },
            )
            for embedded_chunk in embedded_chunks
        ]

        # Upsert the points into the collection
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search(self, query: str, k: int = 10) -> list[EmbeddedChunk]:
        pass
