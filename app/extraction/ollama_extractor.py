from ollama import Client

from app.config.graph_schema import GraphSchema
from app.extraction.extractor import Extractor
from app.extraction.prompt_builder import build_prompt
from app.extraction.schemas.extracted_knowledge_response import (
    ExtractedKnowledgeResponse,
)
from app.graph.entity import Entity
from app.graph.extracted_knowledge import ExtractedKnowledge
from app.graph.relationship import Relationship
from app.models.chunk import Chunk


class OllamaExtractor(Extractor):
    def __init__(
        self,
        schema: GraphSchema,
        model: str = "qwen2.5:3b",
    ):
        self.schema = schema
        self.model = model
        self.client = Client()

    def extract(self, chunk: Chunk) -> ExtractedKnowledge:
        prompt = build_prompt(chunk, self.schema)

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert information extraction system. "
                        "Return only valid JSON matching the provided schema."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            format=ExtractedKnowledgeResponse.model_json_schema(),
            options={
                "temperature": 0,
            },
        )

        validated_response = (
            ExtractedKnowledgeResponse.model_validate_json(
                response.message.content
            )
        )

        entities = [
            Entity(
                id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
            )
            for entity in validated_response.entities
        ]

        relationships = [
            Relationship(
                source=relationship.source,
                target=relationship.target,
                relationship_type=relationship.relationship_type,
                description=relationship.description,
            )
            for relationship in validated_response.relationships
        ]

        return ExtractedKnowledge(
            source_chunk=chunk,
            entities=entities,
            relationships=relationships,
        )