from openai import OpenAI

from app.graph.entity import Entity
from app.resolution.entity_matcher import EntityMatcher
from app.resolution.match_prompt import build_match_prompt
from app.resolution.match_response import build_match_response


class OpenAIEntityMatcher(EntityMatcher):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        # api_key=None -> the SDK reads OPENAI_API_KEY from the environment.
        self.client = OpenAI(api_key=api_key)

    def match_entity(
        self,
        entity: Entity,
        entity_relationships: list[str],
        source_text: str,
        candidates: list[dict],
        candidate_relationships: dict[str, list[str]],
    ) -> str | None:
        prompt = build_match_prompt(
            entity,
            entity_relationships,
            source_text,
            candidates,
            candidate_relationships,
        )
        response_model = build_match_response([c["id"] for c in candidates])

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an entity resolution assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=response_model,
            temperature=0,
        )

        match = completion.choices[0].message.parsed.match
        return None if match == "none" else match
