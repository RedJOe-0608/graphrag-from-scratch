from openai import OpenAI

from app.evaluation.answer_relevance.models import GeneratedQuestions
from app.evaluation.answer_relevance.question_generator import QuestionGenerator
from app.evaluation.answer_relevance.question_prompt import build_question_prompt


class OpenAIQuestionGenerator(QuestionGenerator):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def generate(self, answer: str, n: int) -> GeneratedQuestions:
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You reverse-generate questions from an answer.",
                },
                {"role": "user", "content": build_question_prompt(answer, n)},
            ],
            response_format=GeneratedQuestions,
            temperature=0,
        )
        return completion.choices[0].message.parsed
