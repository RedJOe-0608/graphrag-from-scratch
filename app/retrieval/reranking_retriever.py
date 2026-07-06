from app.models.chunk import Chunk
from app.reranking.reranker import Reranker
from app.retrieval.retriever import Retriever


class RerankingRetriever(Retriever):
    """
    Two-stage retrieval. The inner retriever (typically the HybridRetriever's
    cheap RRF fusion) casts a wide net and returns `candidate_pool` chunks; the
    reranker then does the expensive cross-encoder scoring on just that pool and
    keeps the top `limit`. RRF is kept precisely because it is cheap — it shrinks
    the candidate set the reranker has to score.
    """

    def __init__(
        self,
        retriever: Retriever,
        reranker: Reranker,
        candidate_pool: int = 20,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.candidate_pool = candidate_pool

    def retrieve(self, query: str, limit: int = 5) -> list[Chunk]:
        candidates = self.retriever.retrieve(query, limit=self.candidate_pool)

        return self.reranker.rerank(query, candidates, limit=limit)
