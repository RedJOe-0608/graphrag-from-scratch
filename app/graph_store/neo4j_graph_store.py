from neo4j import GraphDatabase

from app.config.app_config import Neo4jConfig
from app.config.graph_schema import GraphSchema
from app.graph.entity import Entity
from app.graph.extracted_knowledge import ExtractedKnowledge
from app.graph.relationship import Relationship
from app.graph_store.graph_store import GraphStore


class Neo4jGraphStore(GraphStore):
    def __init__(
        self,
        config: Neo4jConfig,
        schema: GraphSchema,
        embedding_dimensions: int
    ):
        self.driver = GraphDatabase.driver(
            config.uri,
            auth=(
                config.username,
                config.password,
            ),
        )

        self.allowed_relationships = set(schema.relationship_types)

        self._create_constraints()
        self._create_vector_index(embedding_dimensions)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.driver.close()
    
    def _create_vector_index(self, dimensions: int):
        with self.driver.session() as session:
            session.run(
                f"""
                CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
                FOR (e:Entity) ON (e.embedding)
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: {dimensions},
                        `vector.similarity_function`: 'cosine'
                    }}
                }}
                """
            )


    def clear(self) -> None:
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def add(self, knowledge: ExtractedKnowledge) -> None:
        with self.driver.session() as session:
            session.execute_write(
                self._merge_entities,
                knowledge.entities,
            )

            for relationship in knowledge.relationships:
                session.execute_write(
                    self._merge_relationship,
                    relationship,
                )

    def _create_constraints(self):
        with self.driver.session() as session:
            session.run(
                """
                CREATE CONSTRAINT entity_id IF NOT EXISTS
                FOR (e:Entity)
                REQUIRE e.id IS UNIQUE
                """
            )

    @staticmethod
    def _merge_entities(tx, entities: list[Entity]):
        tx.run(
            """
            UNWIND $entities AS entity

            MERGE (e:Entity {id: entity.id})

            SET
                e.name = entity.name,
                e.type = entity.type,
                e.description = entity.description,
                e.aliases = entity.aliases,
                e.embedding = entity.embedding,
                e.source_chunk_ids = entity.source_chunk_ids
            """,
            entities=[
                {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.entity_type,
                    "description": entity.description,
                    "aliases": entity.aliases,
                    "embedding": entity.embedding,
                    "source_chunk_ids": entity.source_chunk_ids,
                }
                for entity in entities
            ],
        )

    def _merge_relationship(
        self,
        tx,
        relationship: Relationship,
    ):
        if relationship.relationship_type not in self.allowed_relationships:
            raise ValueError(
                f"Unknown relationship type: "
                f"{relationship.relationship_type}"
            )

        query = f"""
        MATCH (source:Entity {{id: $source}})
        MATCH (target:Entity {{id: $target}})

        MERGE (source)-[r:{relationship.relationship_type}]->(target)

        SET
            r.description = $description
        """

        tx.run(
            query,
            source=relationship.source,
            target=relationship.target,
            description=relationship.description,
        )

    def find_similar_entities(
    self,
    entity_type: str,
    embedding: list[float],
    k: int = 5,
    ) -> list[dict]:
        # O(n) over all entities of this type — exact cosine similarity,
        # no ANN index used. Fine at current scale; revisit if entity
        # counts per type grow large enough that this becomes slow.
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity {type: $entity_type})
                RETURN
                    e.id AS id,
                    e.name AS name,
                    e.description AS description,
                    e.aliases AS aliases,
                    e.source_chunk_ids AS source_chunk_ids,
                    vector.similarity.cosine(e.embedding, $embedding) AS score
                ORDER BY score DESC
                LIMIT $k
                """,
                entity_type=entity_type,
                embedding=embedding,
                k=k,
            )
            return [dict(record) for record in result]

    def upsert_entity(self, entity: Entity) -> None:
        with self.driver.session() as session:
            session.execute_write(self._merge_entities, [entity])

    def get_relationships(self, entity_id: str) -> list[dict]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity {id: $entity_id})-[r]-(other:Entity)
                RETURN
                type(r) AS type,
                r.description AS description,
                CASE WHEN startNode(r) = e THEN 'out' ELSE 'in' END AS direction,
                other.id AS other_id,
                other.name AS other_name,
                other.type AS other_type,
                other.source_chunk_ids AS other_source_chunk_ids

                """,
                entity_id=entity_id,
            )
            return [dict(record) for record in result]


    def add_relationship(self, relationship: Relationship) -> None:
        with self.driver.session() as session:
            session.execute_write(self._merge_relationship, relationship)

