from collections import Counter
from dataclasses import dataclass, field

from app.embeddings.embedder import Embedder
from app.extraction.query_entity_extractor import QueryEntityExtractor
from app.graph.entity import build_entity_embedding_text
from app.graph.graph_fact import GraphFact
from app.graph_store.graph_store import GraphStore


@dataclass
class GraphTraversalResult:
    # How often each chunk id was reached via the query's entities (anchors and
    # their neighbours); GraphRetriever ranks chunks by this count.
    chunk_id_counts: Counter[str] = field(default_factory=Counter)
    # The relationships encountered on the walk, oriented source --> target and
    # deduplicated; the engine feeds these to the LLM as facts.
    facts: list[GraphFact] = field(default_factory=list)


class GraphTraversal:
    """
    The single graph walk behind both graph-based retrievers.

    Given a query it extracts entities, anchors them to similar graph entities,
    and follows their relationships. That one walk yields *both* the chunk ids to
    retrieve (for GraphRetriever, inside the RRF fusion) and the relationship
    facts (read by the engine for the LLM context) — so neither side has to
    repeat the walk or the LLM entity-extraction call.

    Because the two consumers ask for their halves separately within one
    engine.query() call, the most-recent query's result is memoised. The cache is
    purely an optimisation: traverse() returns the same result on a hit or a
    miss, so nothing about correctness depends on call order.

    The cache is a single mutable slot and so assumes one query at a time (true
    for the current CLI). If this is ever driven concurrently on a shared
    instance, guard the cache with a lock or key it per-query.
    """

    def __init__(
        self,
        graph_store: GraphStore,
        embedder: Embedder,
        query_extractor: QueryEntityExtractor,
        k: int = 5,
        max_facts: int = 20,
    ) -> None:
        self.graph_store = graph_store
        self.embedder = embedder
        self.query_extractor = query_extractor
        self.k = k
        # Bound the facts sent to the LLM: a highly-connected anchor (a
        # "supernode") can have hundreds of edges, which would swamp the prompt.
        # Facts are collected best-anchor-first, so the cap keeps the most
        # relevant ones. Chunk counting is unaffected — it always sees the full walk.
        self.max_facts = max_facts
        self._cache: tuple[str, GraphTraversalResult] | None = None

    def traverse(self, query: str) -> GraphTraversalResult:
        if self._cache is not None and self._cache[0] == query:
            return self._cache[1]

        result = self._walk(query)
        self._cache = (query, result)
        return result

    def _walk(self, query: str) -> GraphTraversalResult:
        query_entities = self.query_extractor.extract(query)

        chunk_id_counts: Counter[str] = Counter()
        facts: list[GraphFact] = []
        seen_facts: set[tuple[str, str, str]] = set()

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

                for rel in self.graph_store.get_relationships(anchor["id"]):
                    chunk_id_counts.update(rel["other_source_chunk_ids"])
                    self._collect_fact(anchor, rel, facts, seen_facts)

        return GraphTraversalResult(chunk_id_counts=chunk_id_counts, facts=facts)

    def _collect_fact(
        self,
        anchor: dict,
        rel: dict,
        facts: list[GraphFact],
        seen_facts: set[tuple[str, str, str]],
    ) -> None:
        if len(facts) >= self.max_facts:
            return

        # Orient the edge so it always reads source --> target, regardless of
        # which side the anchor sits on.
        if rel["direction"] == "out":
            source, target = anchor["name"], rel["other_name"]
        else:
            source, target = rel["other_name"], anchor["name"]

        key = (source, rel["type"], target)
        if key in seen_facts:
            return

        seen_facts.add(key)
        facts.append(
            GraphFact(
                source=source,
                relationship_type=rel["type"],
                target=target,
                description=rel.get("description"),
            )
        )
