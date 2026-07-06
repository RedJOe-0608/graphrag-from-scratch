from openai import OpenAI

from app.evaluation.context_recall.attribution_judge import AttributionJudge
from app.evaluation.context_recall.attribution_prompt import build_attribution_prompt
from app.evaluation.context_recall.models import (
    AttributionVerdict,
    AttributionVerdictList,
)


class OpenAIAttributionJudge(AttributionJudge):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def attribute(
        self, ground_truth: str, contexts: list[str]
    ) -> list[AttributionVerdict]:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You attribute ground-truth claims to retrieved context.",
                },
                {
                    "role": "user",
                    "content": build_attribution_prompt(ground_truth, contexts),
                },
            ],
            response_format=AttributionVerdictList,
            temperature=0,
        )
        return completion.choices[0].message.parsed.verdicts
