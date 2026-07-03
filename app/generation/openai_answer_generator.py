from openai import OpenAI

from app.generation.answer_generator import AnswerGenerator
from app.generation.answer_prompt_builder import build_answer_prompt


class OpenAIAnswerGenerator(AnswerGenerator):
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ):
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def generate(self, query: str, context: str) -> str:
        prompt = build_answer_prompt(query, context)

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a careful, grounded question-answering assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        return completion.choices[0].message.content
