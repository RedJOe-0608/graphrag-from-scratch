from abc import ABC, abstractmethod

from app.evaluation.context_recall.models import AttributionVerdict


class AttributionJudge(ABC):
    @abstractmethod
    def attribute(
        self, ground_truth: str, contexts: list[str]
    ) -> list[AttributionVerdict]:
        """
        Break the ground-truth answer into atomic claims, then for each claim
        decide whether it can be attributed to (supported by) the retrieved
        contexts. One verdict per claim.
        """
        pass
