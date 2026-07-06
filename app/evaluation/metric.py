from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EvalSample:
    """
    One row of an evaluation. `question` + `ground_truth` are the *labels*;
    `answer` + `contexts` are what the system actually produced for that question
    (the generated answer and the retrieved chunk texts). A metric reads whichever
    fields it needs and ignores the rest.
    """
    question: str
    answer: str
    contexts: list[str] = field(default_factory=list)  # retrieved chunk texts
    ground_truth: str | None = None  # gold answer; only needed by context_recall


class Metric(ABC):
    """
    Uniform contract so a runner can hold a list[Metric] and score them the same
    way, regardless of what each one does internally. `name` labels the metric in
    reports; `score` returns a value in [0, 1] (higher is better).
    """

    name: str

    @abstractmethod
    def score(self, sample: EvalSample) -> float:
        pass
