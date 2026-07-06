from app.embeddings.embedder import Embedder
from app.evaluation.answer_relevance.question_generator import QuestionGenerator
from app.evaluation.metric import EvalSample, Metric
from app.evaluation.similarity import cosine_similarity


class AnswerRelevance(Metric):
    name = "answer_relevance"

    def __init__(
        self,
        generator: QuestionGenerator,
        embedder: Embedder,
        n_questions: int = 3,
    ):
        self._generator = generator
        self._embedder = embedder
        self._n = n_questions

    def score(self, sample: EvalSample) -> float:
        generated = self._generator.generate(sample.answer, self._n)

        # Evasive answers aren't relevant to anything, no matter how they embed.
        if generated.noncommittal or not generated.questions:
            return 0.0

        # Embed the real question and the reverse-generated ones in one batch;
        # the first vector is the original, the rest are the generated questions.
        embeddings = self._embedder.embed_text([sample.question] + generated.questions)
        original = embeddings[0]
        reverse_questions = embeddings[1:]

        sims = [cosine_similarity(original, q) for q in reverse_questions]
        return sum(sims) / len(sims)
