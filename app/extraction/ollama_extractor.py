from ollama import Client
from pydantic import BaseModel

from app.config.app_config import OllamaConfig
from app.config.graph_schema import GraphSchema
from app.extraction.extractor import Extractor
from app.extraction.prompt_builder import build_prompt
from app.extraction.schemas.extracted_knowledge_response import (
    build_extracted_knowledge_response,
)
from app.graph.entity import Entity
from app.graph.extracted_knowledge import ExtractedKnowledge
from app.graph.relationship import Relationship
from app.models.chunk import Chunk


class OllamaExtractor(Extractor):
    def __init__(
        self,
        config: OllamaConfig,
        schema: GraphSchema,
        client: Client | None = None,
    ):
        self.schema = schema
        self.model = config.model
        self.client = client or Client(
            host=config.host,
        )
        self.response_model = build_extracted_knowledge_response(schema)

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
            format=self.response_model.model_json_schema(), # generates the rulebook for ollama's constrained decoding.
            options={
                "temperature": 0,
            },
        )

        # 1. The model hit max_token limit. So incomplete json response.
        # 2. Network failure. 
        # In both of the cases above, the model_validate_json would raise Pydantic's own ValidationError
        try:
            validated_response = self.response_model.model_validate_json(
                response.message.content
            )
        except Exception as e:
            raise ValueError(
                "Failed to parse Ollama response:\n\n"
                f"{response.message.content}"
            ) from e

        return ExtractedKnowledge(
            source_chunk=chunk,
            entities=self._build_entities(validated_response),
            relationships=self._build_relationships(validated_response),
        )

    @staticmethod
    def _build_entities(
        validated_response: BaseModel,
    ) -> list[Entity]:
        return [
            Entity(
                id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
            )
            for entity in validated_response.entities
        ]

    @staticmethod
    def _build_relationships(
        validated_response: BaseModel,
    ) -> list[Relationship]:
        return [
            Relationship(
                source=relationship.source,
                target=relationship.target,
                relationship_type=relationship.relationship_type,
                description=relationship.description,
            )
            for relationship in validated_response.relationships
        ]