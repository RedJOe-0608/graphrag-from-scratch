import os
import pickle
import re

from rank_bm25 import BM25Okapi

from app.config.app_config import KeywordConfig
from app.keyword_store.keyword_store import KeywordStore
from app.models.chunk import Chunk


class BM25KeywordStore(KeywordStore):
    def __init__(self, config: KeywordConfig) -> None:
        self.index_path = config.index_path

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        # rank_bm25 has no incremental "add one document" — the index is
        # rebuilt from the full corpus on every add. Fine at this scale; it is
        # exactly why production engines (Lucene/Elasticsearch) use incremental
        # inverted indexes instead. Marker for when the corpus outgrows this.
        existing = self._load_chunks()

        # Dedup by id so re-ingesting a document replaces its chunks rather than
        # duplicating them — mirrors Qdrant's upsert-by-id semantics.
        by_id = {chunk.id: chunk for chunk in existing}
        for chunk in chunks:
            by_id[chunk.id] = chunk

        self._build_and_save(list(by_id.values()))

    def search(self, query: str, limit: int = 5) -> list[Chunk]:
        state = self._load()
        if state is None:
            return []

        bm25: BM25Okapi = state["bm25"]
        chunks: list[Chunk] = state["chunks"]

        # get_scores returns one BM25 score per chunk, aligned to `chunks`.
        scores = bm25.get_scores(self._tokenize(query))

        ranked = sorted(
            range(len(chunks)),
            key=lambda i: scores[i],
            reverse=True,
        )

        results: list[Chunk] = []
        for i in ranked[:limit]:
            # A zero score means no query term appears in the chunk — it is not
            # a keyword match, so don't pass it downstream as one. Since `ranked`
            # is descending, everything after the first zero is also zero.
            if scores[i] <= 0:
                break
            results.append(chunks[i])

        return results

    def clear(self) -> None:
        if os.path.exists(self.index_path):
            os.remove(self.index_path)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        # Lowercase, then keep runs of letters/digits. Deliberately simple and
        # transparent — no stemming or stopword removal yet, so you can see raw
        # BM25 behavior before adding refinements.
        return re.findall(r"[a-z0-9]+", text.lower())

    def _build_and_save(self, chunks: list[Chunk]) -> None:
        tokenized_corpus = [self._tokenize(chunk.text) for chunk in chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        # Persist the built index (Layer 2) itself — not just the chunks — so a
        # query process loads a ready-to-score index and skips the rebuild.
        # NOTE: pickle is coupled to the rank_bm25/Python version; a version
        # bump can invalidate the file. Fine for learning; production uses a
        # purpose-built index format.
        self._save({"bm25": bm25, "chunks": chunks})

    def _load(self) -> dict | None:
        if not os.path.exists(self.index_path):
            return None
        with open(self.index_path, "rb") as file:
            return pickle.load(file)

    def _load_chunks(self) -> list[Chunk]:
        state = self._load()
        return state["chunks"] if state else []

    def _save(self, state: dict) -> None:
        directory = os.path.dirname(self.index_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.index_path, "wb") as file:
            pickle.dump(state, file)
