from app.evaluation.faithfulness.faithfulness_judge import FaithfulnessJudge
from app.evaluation.metric import EvalSample, Metric

# Is the answer grounded in the retrived context, or did the model make things up? It's the hallucination detector. 
# So remember, this is NOT correctedness. This is faithfulness.
# This is essentially LLM-as-a-judge pattern: use an LLM to grade an LLM.

class Faithfulness(Metric):
    name = "faithfulness"

    def __init__(self, judge: FaithfulnessJudge):
        self._judge = judge

    def score(self, sample: EvalSample) -> float:
        answer = sample.answer
        context = "\n\n".join(sample.contexts)

        claims = self._judge.extract_claims(answer)

        # No factual claims (e.g. "I don't know") -> nothing to hallucinate -> vacuously faithful.
        if not claims:
            return 1.0

        verdicts = self._judge.verify_claims(claims, context)
        supported = sum(v.supported for v in verdicts)
        return supported / len(verdicts)
