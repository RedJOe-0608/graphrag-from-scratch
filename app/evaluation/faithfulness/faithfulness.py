from app.evaluation.faithfulness.faithfulness_judge import FaithfulnessJudge


class Faithfulness:
    def __init__(self, judge: FaithfulnessJudge):
        self._judge = judge

    def score(self, answer: str, context: str) -> float:
        claims = self._judge.extract_claims(answer)

        # No factual claims (e.g. "I don't know") -> nothing to hallucinate -> vacuously faithful.
        if not claims:
            return 1.0

        verdicts = self._judge.verify_claims(claims, context)
        supported = sum(v.supported for v in verdicts)
        return supported / len(verdicts)
