from openai import OpenAI

from app.evaluation.faithfulness.faithfulness_judge import FaithfulnessJudge
from app.evaluation.faithfulness.models import ClaimList, ClaimVerdict, VerdictList
from app.evaluation.faithfulness.claim_prompt import build_claim_prompt
from app.evaluation.faithfulness.verdict_prompt import build_verdict_prompt


class OpenAIFaithfulnessJudge(FaithfulnessJudge):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def extract_claims(self, answer: str) -> list[str]:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": "You break answers into atomic factual claims."},
                {"role": "user", "content": build_claim_prompt(answer)},
            ],
            response_format=ClaimList,
            temperature=0,
        )
        return completion.choices[0].message.parsed.claims

    def verify_claims(self, claims: list[str], context: str) -> list[ClaimVerdict]:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": "You verify claims strictly against provided context."},
                {"role": "user", "content": build_verdict_prompt(claims, context)},
            ],
            response_format=VerdictList,
            temperature=0,
        )
        return completion.choices[0].message.parsed.verdicts

