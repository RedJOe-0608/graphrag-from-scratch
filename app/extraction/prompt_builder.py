from app.config.graph_schema import GraphSchema
from app.models.chunk import Chunk


def build_prompt(chunk: Chunk, schema: GraphSchema) -> str:
    entity_types = "\n".join(f"- {entity}" for entity in schema.entity_types)
    relationship_types = "\n".join(
        f"- {relationship}" for relationship in schema.relationship_types
    )

    return f"""
You are an expert information extraction system.

Your task is to extract entities and relationships from the provided text.

## Rules

1. Use ONLY the allowed entity types.
2. Use ONLY the allowed relationship types.
3. Generate entity IDs in lowercase snake_case.
4. Entity IDs must be unique within this response.
5. Every relationship's source and target MUST be the id of an entity you listed in the "entities" array. If a relationship mentions an entity, you MUST also add that entity to the "entities" array. NEVER reference an id that is not in the entities list.
6. Do not invent entities or relationships that are not supported by the text.
7. If no entities or relationships exist, return empty lists.
8. Return ONLY valid JSON.
9. Do NOT wrap the JSON in markdown.
10. Do NOT include explanations, notes, or additional text.
11. Every entity MUST include a "description": one or two sentences describing the entity using ONLY facts stated in the text. Do not use outside knowledge.

## Allowed Entity Types

{entity_types}

## Allowed Relationship Types

{relationship_types}

## JSON Format

{{
  "entities": [
    {{
      "id": "sam_altman",
      "name": "Sam Altman",
      "entity_type": "Person",
      "description": "CEO of OpenAI"
    }}
  ],
  "relationships": [
    {{
      "source": "sam_altman",
      "target": "openai",
      "relationship_type": "WORKS_AT",
      "description": "Sam Altman works at OpenAI"
    }}
  ]
}}

## Text

{chunk.text}
"""