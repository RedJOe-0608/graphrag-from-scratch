def build_answer_prompt(query: str, context: str) -> str:
    return f"""
You are a question-answering assistant.

Answer the question using ONLY the information in the sources below. If the
sources do not contain enough information to answer, say so explicitly rather
than guessing or using outside knowledge.

## Sources

{context}

## Question

{query}
"""
