from abc import ABC, abstractmethod


class AnswerGenerator(ABC):
    @abstractmethod
    def generate(self, query: str, context: str) -> str:
        """
        Return an answer to the query, grounded in the given context.
        """
        pass
