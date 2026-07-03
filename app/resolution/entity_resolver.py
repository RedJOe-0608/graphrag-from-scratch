from dataclasses import replace
from uuid import uuid4

from app.embeddings.embedder import Embedder
from app.graph.entity import Entity, build_entity_embedding_text
from app.graph.extracted_knowledge import ExtractedKnowledge
from app.graph_store.graph_store import GraphStore
from app.resolution.entity_matcher import EntityMatcher


class EntityResolver:
    def __init__(
        self,
        graph_store: GraphStore,
        embedder: Embedder,
        matcher: EntityMatcher,
        low_threshold: float,
        k: int = 5,
    ):
        self.graph_store = graph_store
        self.embedder = embedder
        self.matcher = matcher
        # Candidates scoring below low_threshold are not even plausible, so they
        # are filtered out before the LLM. There is deliberately no HIGH
        # auto-merge band: observed similarity scores for true vs false merges
        # overlap (e.g. a wrong Toronto/Austin merge scored higher than some
        # correct Northwind merges), so no threshold can safely auto-merge. The
        # LLM is the sole arbiter for any plausible candidate.
        self.low_threshold = low_threshold
        self.k = k

    def resolve_knowledge(self, knowledge: ExtractedKnowledge) -> int:
        """
        Resolve every entity in the chunk to a canonical id, then rewrite
        each relationship's source/target through that {local_id: canonical_id}
        map before writing. Returns the number of relationships actually written.
        """
        id_map: dict[str, str] = {}
        local_names = {e.id: e.name for e in knowledge.entities}
        rels_by_entity = self._relationships_by_entity(knowledge, local_names)
        source_text = knowledge.source_chunk.text

        for entity in knowledge.entities:
            entity_relationships = rels_by_entity.get(entity.id, [])
            canonical_id = self.resolve(entity, entity_relationships, source_text)
            id_map[entity.id] = canonical_id

        relationships_written = 0

        for relationship in knowledge.relationships:
            source = id_map.get(relationship.source)
            target = id_map.get(relationship.target)

            # A relationship can reference an entity id that was never declared
            # in this chunk's entity list (the extractor occasionally does this).
            # Without a canonical id we cannot remap it, and Neo4j's MATCH would
            # silently drop the edge — so skip it explicitly instead.
            if source is None or target is None:
                continue

            remapped = replace(
                relationship,
                source=source,
                target=target,
            )
            self.graph_store.add_relationship(remapped)
            relationships_written += 1

        return relationships_written

    def resolve(
        self,
        entity: Entity,
        entity_relationships: list[str],
        source_text: str,
    ) -> str:
        embedding = self.embedder.embed_text(
            [build_entity_embedding_text(entity)]
        )[0]
        candidates = self.graph_store.find_similar_entities(
            entity_type=entity.entity_type,
            embedding=embedding,
            k=self.k,
        )
        plausible = [c for c in candidates if c["score"] >= self.low_threshold]
        label = f"{entity.name!r} [{entity.entity_type}]"

        if not plausible:
            best = (
                f"{candidates[0]['name']!r} {candidates[0]['score']:.3f}"
                if candidates
                else "none"
            )
            print(f"  NEW      {label} (no plausible candidate; best={best})")
            return self._create(entity)

        candidate_relationships = {
            c["id"]: self._render_candidate_relationships(c["id"])
            for c in plausible
        }
        match_id = self.matcher.match_entity(
            entity=entity,
            entity_relationships=entity_relationships,
            source_text=source_text,
            candidates=plausible,
            candidate_relationships=candidate_relationships,
        )

        if match_id is None:
            names = ", ".join(
                f"{c['name']!r}({c['score']:.2f})" for c in plausible
            )
            print(f"  NEW      {label} (LLM: none of [{names}])")
            return self._create(entity)

        matched = next(c for c in plausible if c["id"] == match_id)
        print(
            f"  MERGE    {label} -> {matched['name']!r} "
            f"(LLM picked, score={matched['score']:.3f})"
        )
        return self._merge(entity, matched)

    def _create(self, entity: Entity) -> str:
        canonical_id = str(uuid4())
        new_entity = replace(entity, id=canonical_id)
        embedding = self.embedder.embed_text(
            [build_entity_embedding_text(new_entity)]
        )[0]
        new_entity = replace(new_entity, embedding=embedding)

        self.graph_store.upsert_entity(new_entity)
        return canonical_id

    def _merge(self, entity: Entity, candidate: dict) -> str:
        aliases = list(candidate["aliases"] or [])

        source_chunk_ids = list(candidate["source_chunk_ids"] or [])
        for chunk_id in entity.source_chunk_ids:
            if chunk_id not in source_chunk_ids:
                source_chunk_ids.append(chunk_id)

        if entity.name != candidate["name"] and entity.name not in aliases:
            aliases.append(entity.name)

        description = "; ".join(
            filter(None, [candidate["description"], entity.description])
        )

        merged_entity = replace(
            entity,
            id=candidate["id"],
            name=candidate["name"],
            description=description,
            aliases=aliases,
            source_chunk_ids=source_chunk_ids,
        )
        embedding = self.embedder.embed_text(
            [build_entity_embedding_text(merged_entity)]
        )[0]
        merged_entity = replace(merged_entity, embedding=embedding)

        self.graph_store.upsert_entity(merged_entity)
        return candidate["id"]

    @staticmethod
    def _relationships_by_entity(
        knowledge: ExtractedKnowledge,
        local_names: dict[str, str],
    ) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for rel in knowledge.relationships:
            src_name = local_names.get(rel.source, rel.source)
            tgt_name = local_names.get(rel.target, rel.target)
            result.setdefault(rel.source, []).append(
                f"-[{rel.relationship_type}]-> {tgt_name}"
            )
            result.setdefault(rel.target, []).append(
                f"<-[{rel.relationship_type}]- {src_name}"
            )
        return result

    def _render_candidate_relationships(self, candidate_id: str) -> list[str]:
        rendered = []
        for r in self.graph_store.get_relationships(candidate_id):
            if r["direction"] == "out":
                rendered.append(f"-[{r['type']}]-> {r['other_name']}")
            else:
                rendered.append(f"<-[{r['type']}]- {r['other_name']}")
        return rendered
