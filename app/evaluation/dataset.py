import json

from app.evaluation.metric import EvalSample


def load_eval_set(path: str) -> list[EvalSample]:
    """
    Load a JSON eval set into EvalSample objects. Each JSON record has:
      question (str), answer (str), contexts (list[str]), ground_truth (str|None).

    Note: in this static form the `answer` and `contexts` are pre-recorded. In a
    live setup you would instead store only question + ground_truth here, run the
    GraphRAGEngine per question to fill answer + contexts, then score.
    """
    with open(path) as f:
        raw = json.load(f)

    return [
        EvalSample(
            question=record["question"],
            answer=record["answer"],
            contexts=record.get("contexts", []),
            ground_truth=record.get("ground_truth"),
        )
        for record in raw
    ]
