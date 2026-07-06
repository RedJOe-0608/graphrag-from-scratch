from openai import OpenAI

from app.evaluation.context_precision.models import RelevanceVerdictList
from app.evaluation.context_precision.relevance_judge import RelevanceJudge
from app.evaluation.context_precision.relevance_prompt import build_relevance_prompt


class OpenAIRelevanceJudge(RelevanceJudge):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def judge_relevance(self, question: str, contexts: list[str]) -> list[bool]:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You judge whether context chunks are relevant to a question.",
                },
                {"role": "user", "content": build_relevance_prompt(question, contexts)},
            ],
            response_format=RelevanceVerdictList,
            temperature=0,
        )
        verdicts = completion.choices[0].message.parsed.verdicts
        return [v.relevant for v in verdicts]
