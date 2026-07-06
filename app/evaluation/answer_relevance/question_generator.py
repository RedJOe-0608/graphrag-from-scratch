from abc import ABC, abstractmethod

from app.evaluation.answer_relevance.models import GeneratedQuestions


class QuestionGenerator(ABC):
    @abstractmethod
    def generate(self, answer: str, n: int) -> GeneratedQuestions:
        """
        Given an answer, reverse-generate `n` questions that this answer would be
        a good response to, and flag whether the answer is noncommittal (evasive).
        """
        pass
