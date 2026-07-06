def build_relevance_prompt(question: str, contexts: list[str]) -> str:
    blocks = "\n\n".join(
        f"[CONTEXT {i + 1}]\n{c}" for i, c in enumerate(contexts)
    )
    return f"""For each context chunk below, decide whether it is relevant and
useful for answering the QUESTION.

Rules:
- Judge each chunk independently.
- A chunk is relevant only if it contains information that helps answer the
  question. Being on the same broad topic is not enough.
- Return exactly one verdict per chunk, in the same order as given.

QUESTION:
{question}

CONTEXTS:
{blocks}
"""
