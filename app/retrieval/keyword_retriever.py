from app.keyword_store.keyword_store import KeywordStore
from app.models.chunk import Chunk
from app.retrieval.retriever import Retriever


class KeywordRetriever(Retriever):
    def __init__(self, keyword_store: KeywordStore) -> None:
        self.keyword_store = keyword_store

    def retrieve(self, query: str, limit: int = 5) -> list[Chunk]:
        return self.keyword_store.search(query, limit=limit)
