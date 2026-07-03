from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config.app_config import QdrantConfig
from app.models.chunk import Chunk
from app.models.embedded_chunk import EmbeddedChunk
from app.vector_store.vector_store import VectorStore


class QdrantVectorStore(VectorStore):
    def __init__(
        self,
        config: QdrantConfig,
        client: QdrantClient | None = None,
    ) -> None:
        self.collection_name = config.collection_name

        self.client = client or QdrantClient(
            host=config.host,
            port=config.port,
        )

    def _create_collection_if_not_exists(
        self,
        vector_size: int,
    ) -> None:
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def add(
        self,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        if not embedded_chunks:
            return

        vector_size = len(embedded_chunks[0].embedding)

        self._create_collection_if_not_exists(vector_size)

        points = [
            PointStruct(
                id=embedded_chunk.chunk.id,
                vector=embedded_chunk.embedding,
                payload={
                    "chunk_id": embedded_chunk.chunk.id,
                    "document_id": embedded_chunk.chunk.document_id,
                    "text": embedded_chunk.chunk.text,
                },
            )
            for embedded_chunk in embedded_chunks
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[EmbeddedChunk]:
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=limit,
            with_payload=True,
            with_vectors=True,
        )

        return [
            EmbeddedChunk(
                chunk=Chunk(
                    id=point.payload["chunk_id"],
                    document_id=point.payload["document_id"],
                    text=point.payload["text"],
                ),
                embedding=point.vector,
            )
            for point in response.points
        ]

    def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=chunk_ids,
            with_payload=True,
        )

        return [
            Chunk(
                id=point.payload["chunk_id"],
                document_id=point.payload["document_id"],
                text=point.payload["text"],
            )
            for point in points
        ]
