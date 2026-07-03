from collections import Counter

from app.embeddings.embedder import Embedder
from app.extraction.query_entity_extractor import QueryEntityExtractor
from app.graph.entity import build_entity_embedding_text
from app.graph_store.graph_store import GraphStore
from app.models.chunk import Chunk
from app.retrieval.retriever import Retriever
from app.vector_store.vector_store import VectorStore


class GraphRetriever(Retriever):
    def __init__(
        self,
        graph_store: GraphStore,
        vector_store: VectorStore,
        embedder: Embedder,
        query_extractor: QueryEntityExtractor,
        k: int = 5,
    ) -> None:
        self.graph_store = graph_store
        self.vector_store = vector_store
        self.embedder = embedder
        self.query_extractor = query_extractor
        self.k = k

    def retrieve(self, query: str, limit: int = 5) -> list[Chunk]:
        query_entities = self.query_extractor.extract(query)

        chunk_id_counts: Counter[str] = Counter()

        for entity in query_entities:
            embedding = self.embedder.embed_text(
                [build_entity_embedding_text(entity)]
            )[0]

            anchors = self.graph_store.find_similar_entities(
                entity_type=entity.entity_type,
                embedding=embedding,
                k=self.k,
            )

            for anchor in anchors:
                chunk_id_counts.update(anchor["source_chunk_ids"])

                for neighbor in self.graph_store.get_relationships(anchor["id"]):
                    chunk_id_counts.update(neighbor["other_source_chunk_ids"])

        if not chunk_id_counts:
            return []

        top_chunk_ids = [
            chunk_id for chunk_id, _ in chunk_id_counts.most_common(limit)
        ]

        return self.vector_store.get_by_ids(top_chunk_ids)
