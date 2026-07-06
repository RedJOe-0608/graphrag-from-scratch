def build_verdict_prompt(claims: list[str], context: str) -> str:
    numbered = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
    return f"""You are checking whether each claim is supported by the CONTEXT below.

Rules:
- Judge ONLY against the context. Do NOT use outside/world knowledge.
- A claim is supported ONLY if the context directly states or clearly implies it.
- If the context is silent on a claim, it is NOT supported (even if true in reality).
- For each claim, give: the claim, supported (true/false), and a short reason.

CONTEXT:
{context}

CLAIMS:
{numbered}
"""
