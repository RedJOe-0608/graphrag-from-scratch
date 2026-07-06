from abc import ABC, abstractmethod

from app.evaluation.faithfulness.models import ClaimVerdict


class FaithfulnessJudge(ABC):
    @abstractmethod
    def extract_claims(self, answer: str) -> list[str]:
        pass

    @abstractmethod
    def verify_claims(self, claims: list[str], context: str) -> list[ClaimVerdict]:
        pass
