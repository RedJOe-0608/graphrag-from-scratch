def build_question_prompt(answer: str, n: int) -> str:
    return f"""Given the ANSWER below, generate {n} distinct questions that this
answer would be a good and complete response to.

Also decide whether the answer is "noncommittal": an evasive answer that dodges
the question (e.g. "I don't know", "the context does not provide this",
"I cannot answer"). Set noncommittal to true for such answers, false otherwise.

Rules:
- Base the questions ONLY on the content of the answer.
- Each question should be answerable by the answer on its own.

ANSWER:
{answer}
"""
