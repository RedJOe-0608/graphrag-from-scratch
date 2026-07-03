from openai import OpenAI
from pydantic import BaseModel

from app.config.graph_schema import GraphSchema
from app.extraction.extractor import Extractor
from app.extraction.prompt_builder import build_prompt
from app.extraction.relationship_validation import build_valid_relationships
from app.extraction.schemas.extracted_knowledge_response import (
    build_extracted_knowledge_response,
)
from app.graph.entity import Entity
from app.graph.extracted_knowledge import ExtractedKnowledge
from app.models.chunk import Chunk


class OpenAIExtractor(Extractor):
    def __init__(
        self,
        schema: GraphSchema,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ):
        self.schema = schema
        self.model = model
        # api_key=None -> the SDK reads OPENAI_API_KEY from the environment.
        self.client = OpenAI(api_key=api_key)
        self.response_model = build_extracted_knowledge_response(schema)

    def extract(self, chunk: Chunk) -> ExtractedKnowledge:
        prompt = build_prompt(chunk, self.schema)

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert information extraction system. "
                        "Return only valid JSON matching the provided schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format=self.response_model,
            temperature=0,
        )

        validated = completion.choices[0].message.parsed
        entities = self._build_entities(validated, chunk.id)

        return ExtractedKnowledge(
            source_chunk=chunk,
            entities=entities,
            relationships=build_valid_relationships(validated, entities, self.schema),
        )

    @staticmethod
    def _build_entities(
        validated_response: BaseModel,
        chunk_id: str,
    ) -> list[Entity]:
        return [
            Entity(
                id=entity.id,
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
                source_chunk_ids=[chunk_id],
            )
            for entity in validated_response.entities
        ]
