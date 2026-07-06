from app.evaluation.context_precision.relevance_judge import RelevanceJudge
from app.evaluation.metric import EvalSample, Metric


class ContextPrecision(Metric):
    name = "context_precision"

    def __init__(self, judge: RelevanceJudge):
        self._judge = judge

    def score(self, sample: EvalSample) -> float:
        if not sample.contexts:
            return 0.0

        relevances = self._judge.judge_relevance(sample.question, sample.contexts)
        total_relevant = sum(relevances)
        if total_relevant == 0:
            return 0.0

        # Rank-aware average precision: reward relevant chunks that appear EARLY.
        # For each relevant chunk at rank k, add precision@k = (# relevant so far / k),
        # then normalise by the total number of relevant chunks.
        weighted_precision = 0.0
        hits = 0
        for k, is_relevant in enumerate(relevances, start=1):
            if is_relevant:
                hits += 1
                weighted_precision += hits / k

        return weighted_precision / total_relevant
