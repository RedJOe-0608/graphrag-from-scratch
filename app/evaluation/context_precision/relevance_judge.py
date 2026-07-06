from abc import ABC, abstractmethod


class RelevanceJudge(ABC):
    @abstractmethod
    def judge_relevance(self, question: str, contexts: list[str]) -> list[bool]:
        """
        For each context chunk (in order), decide whether it is relevant/useful
        for answering the question. Returns a list of booleans aligned 1:1 with
        the input `contexts`.
        """
        pass
