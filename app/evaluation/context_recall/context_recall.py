from app.evaluation.context_recall.attribution_judge import AttributionJudge
from app.evaluation.metric import EvalSample, Metric


class ContextRecall(Metric):
    name = "context_recall"

    def __init__(self, judge: AttributionJudge):
        self._judge = judge

    def score(self, sample: EvalSample) -> float:
        if sample.ground_truth is None:
            raise ValueError("context_recall requires a ground_truth answer.")

        verdicts = self._judge.attribute(sample.ground_truth, sample.contexts)

        # A ground truth with no extractable claims can't be "missed" -> vacuously 1.0.
        if not verdicts:
            return 1.0

        attributed = sum(v.attributed for v in verdicts)
        return attributed / len(verdicts)
