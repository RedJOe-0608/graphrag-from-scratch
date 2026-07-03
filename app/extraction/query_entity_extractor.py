from uuid import uuid4

from openai import OpenAI

from app.config.graph_schema import GraphSchema
from app.extraction.query_prompt_builder import build_query_prompt
from app.extraction.schemas.query_entities_response import (
    build_query_entities_response,
)
from app.graph.entity import Entity


class QueryEntityExtractor:
    def __init__(
        self,
        schema: GraphSchema,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ):
        self.schema = schema
        self.model = model
        self.client = OpenAI(api_key=api_key)
        self.response_model = build_query_entities_response(schema.entity_types)

    def extract(self, query: str) -> list[Entity]:
        prompt = build_query_prompt(query, self.schema)

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert entity recognition system. "
                        "Return only valid JSON matching the provided schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format=self.response_model,
            temperature=0,
        )

        validated = completion.choices[0].message.parsed

        return [
            Entity(
                id=str(uuid4()),
                name=entity.name,
                entity_type=entity.entity_type,
            )
            for entity in validated.entities
        ]
