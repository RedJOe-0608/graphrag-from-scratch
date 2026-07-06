from app.config.app_config import KeywordConfig
from app.keyword_store.bm25_keyword_store import BM25KeywordStore
from app.models.chunk import Chunk

# A corpus big enough that BM25's IDF is meaningful. On a 2-3 doc corpus a term
# appearing in ~half the docs gets zero/negative IDF, so scores collapse to <= 0
# and every result is filtered out — using a handful of docs avoids that trap.
CORPUS = [
    Chunk(id="0", document_id="d", text="Northwind Traders was founded by Maria Chen in 2010"),
    Chunk(id="1", document_id="d", text="Globex Corporation acquired Northwind Traders in 2021"),
    Chunk(id="2", document_id="d", text="The quarterly revenue report showed strong growth in Europe"),
    Chunk(id="3", document_id="d", text="Maria Chen previously worked at a logistics startup in Berlin"),
    Chunk(id="4", document_id="d", text="Globex is a multinational conglomerate headquartered in Chicago"),
    Chunk(id="5", document_id="d", text="Supply chain disruptions affected shipping costs across the region"),
    Chunk(id="6", document_id="d", text="The merger created the largest trading firm in the sector"),
    Chunk(id="7", document_id="d", text="Annual shipping volumes increased despite rising fuel prices"),
]


def test_returns_chunks_matching_query_terms(keyword_store):
    keyword_store.add(CORPUS)

    results = keyword_store.search("Maria Chen", limit=5)
    ids = {chunk.id for chunk in results}

    # Both Maria Chen chunks should surface; an unrelated chunk should not.
    assert "0" in ids
    assert "3" in ids
    assert "2" not in ids


def test_ranks_chunk_with_more_query_terms_first(keyword_store):
    keyword_store.add(CORPUS)

    results = keyword_store.search("Maria Chen Berlin", limit=5)
    ids = [chunk.id for chunk in results]

    # Chunk 3 matches maria + chen + berlin; chunk 0 matches only maria + chen,
    # so the richer match must rank ahead.
    assert ids.index("3") < ids.index("0")


def test_returns_empty_when_no_terms_match(keyword_store):
    keyword_store.add(CORPUS)

    # No query term appears in any chunk -> every score is 0 -> filtered out.
    assert keyword_store.search("quantum entanglement") == []


def test_search_on_empty_store_returns_empty(keyword_store):
    # Nothing indexed and no file on disk yet.
    assert keyword_store.search("Maria Chen") == []


def test_respects_limit(keyword_store):
    keyword_store.add(CORPUS)

    results = keyword_store.search("Globex Northwind Maria shipping", limit=2)

    assert len(results) <= 2


def test_add_dedups_by_id(keyword_store):
    keyword_store.add(CORPUS)
    # Re-adding the same ids (with changed text) must replace, not duplicate.
    keyword_store.add([
        Chunk(id="0", document_id="d", text="Northwind Traders was founded by Maria Chen in 2010"),
    ])

    results = keyword_store.search("Maria Chen", limit=10)
    ids = [chunk.id for chunk in results]

    assert ids.count("0") == 1


def test_persists_index_across_instances(keyword_store):
    keyword_store.add(CORPUS)

    # A brand-new store pointed at the same file, with no add() call, must still
    # answer — proving the built index was loaded from disk, not from memory.
    reloaded = BM25KeywordStore(
        config=KeywordConfig(index_path=keyword_store.index_path)
    )
    results = reloaded.search("Globex", limit=5)

    assert results
    assert all(chunk.id in {"1", "4"} for chunk in results)


def test_clear_removes_index(keyword_store):
    keyword_store.add(CORPUS)
    keyword_store.clear()

    assert keyword_store.search("Maria Chen") == []
