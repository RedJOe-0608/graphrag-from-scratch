from pydantic import BaseModel


class GeneratedQuestions(BaseModel):
    questions: list[str]  # questions the given answer would be a good response to
    # True if the answer is evasive / dodges the question (e.g. "I don't know",
    # "the context does not say"). Such answers get relevance 0 regardless of
    # similarity, because there is no real answer to be relevant.
    noncommittal: bool
