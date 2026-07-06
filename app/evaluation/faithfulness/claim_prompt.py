def build_claim_prompt(answer: str) -> str:
    return f"""Break the following answer into a list of atomic factual claims.

Rules:
- Each claim must be a single, standalone fact.
- Resolve pronouns (no "it"/"they" — name the subject).
- Only use information present in the answer; do not add anything.

ANSWER:
{answer}
"""
