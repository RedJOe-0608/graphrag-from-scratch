from ollama import Client

from app.config.app_config import OllamaConfig
from app.graph.entity import Entity
from app.resolution.entity_matcher import EntityMatcher
from app.resolution.match_prompt import build_match_prompt
from app.resolution.match_response import build_match_response


class OllamaEntityMatcher(EntityMatcher):
    def __init__(self, config: OllamaConfig, client: Client | None = None):
        self.model = config.model
        self.client = client or Client(host=config.host)

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

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an entity resolution assistant. "
                        "Return only valid JSON matching the provided schema."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            format=response_model.model_json_schema(),
            options={"temperature": 0},
        )

        try:
            validated = response_model.model_validate_json(response.message.content)
        except Exception as e:
            raise ValueError(
                "Failed to parse Ollama response:\n\n"
                f"{response.message.content}"
            ) from e

        return None if validated.match == "none" else validated.match
