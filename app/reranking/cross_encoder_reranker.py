import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.models.chunk import Chunk
from app.reranking.reranker import Reranker


class CrossEncoderReranker(Reranker):
    """
    Reranks chunks with a cross-encoder: unlike the bi-encoder embeddings used
    for retrieval (query and chunk embedded separately, then compared), a
    cross-encoder feeds the (query, chunk) pair through the model together and
    outputs a single relevance score. This is far more accurate but far more
    expensive — one forward pass per chunk — which is why we only run it on the
    handful of candidates the cheap RRF fusion already surfaced.
    """

    def __init__(
        self,
        model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        max_length: int = 512,
    ) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.model = AutoModelForSequenceClassification.from_pretrained(model)
        self.model.eval()
        self.max_length = max_length

    def rerank(self, query: str, chunks: list[Chunk], limit: int = 5) -> list[Chunk]:
        if not chunks:
            return []

        features = self.tokenizer(
            [query] * len(chunks),
            [chunk.text for chunk in chunks],
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        with torch.no_grad():
            logits = self.model(**features).logits.squeeze(-1)

        scores = logits.tolist()
        # A single-chunk batch squeezes down to a scalar; normalise to a list.
        if not isinstance(scores, list):
            scores = [scores]

        ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)

        return [chunk for chunk, _ in ranked[:limit]]
