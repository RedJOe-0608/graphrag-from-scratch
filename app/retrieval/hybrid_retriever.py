from collections import defaultdict

from app.models.chunk import Chunk
from app.retrieval.retriever import Retriever


class HybridRetriever(Retriever):
    def __init__(
        self,
        retrievers: list[Retriever],
        rrf_k: int = 60,
        fetch_multiplier: int = 4,
    ) -> None:
        self.retrievers = retrievers
        self.rrf_k = rrf_k
        self.fetch_multiplier = fetch_multiplier

    def retrieve(self, query: str, limit: int = 5) -> list[Chunk]:
        fetch_n = limit * self.fetch_multiplier

        scores: dict[str, float] = defaultdict(float)
        chunk_by_id: dict[str, Chunk] = {}

        for retriever in self.retrievers:
            for rank, chunk in enumerate(retriever.retrieve(query, limit=fetch_n), start=1):
                scores[chunk.id] += 1 / (self.rrf_k + rank)
                chunk_by_id[chunk.id] = chunk

        top_ids = sorted(scores, key=scores.get, reverse=True)[:limit]

        return [chunk_by_id[chunk_id] for chunk_id in top_ids]
