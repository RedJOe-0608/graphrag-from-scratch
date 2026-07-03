from app.config.graph_schema import GraphSchema


def build_query_prompt(query: str, schema: GraphSchema) -> str:
    entity_types = "\n".join(f"- {entity}" for entity in schema.entity_types)

    return f"""
You are an expert entity recognition system.

Your task is to identify every entity mentioned or referenced in the user's
question below.

## Rules

1. Use ONLY the allowed entity types.
2. Identify an entity even if the question only asks about it and states no
   facts about it (e.g. "Where does X work?" still mentions X).
3. Do NOT invent entities that are not mentioned or referenced in the question.
4. Do NOT include a description — only name and entity_type.
5. Return ONLY valid JSON.
6. Do NOT wrap the JSON in markdown.
7. Do NOT include explanations, notes, or additional text.

## Allowed Entity Types

{entity_types}

## JSON Format

{{
  "entities": [
    {{
      "name": "Sam Altman",
      "entity_type": "Person"
    }}
  ]
}}

## Question

{query}
"""
