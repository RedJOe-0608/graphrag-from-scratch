from app.evaluation.metric import EvalSample, Metric


class EvaluationRunner:
    """
    Runs a set of metrics over a set of samples and reports the mean score per
    metric. Treats every metric uniformly through the Metric ABC, which is the
    whole reason that shared contract exists.
    """

    def __init__(self, metrics: list[Metric]):
        self._metrics = metrics

    def run(self, samples: list[EvalSample]) -> dict[str, float]:
        if not samples:
            return {metric.name: 0.0 for metric in self._metrics}

        totals: dict[str, float] = {metric.name: 0.0 for metric in self._metrics}
        for sample in samples:
            for metric in self._metrics:
                totals[metric.name] += metric.score(sample)

        return {name: total / len(samples) for name, total in totals.items()}
