def build_attribution_prompt(ground_truth: str, contexts: list[str]) -> str:
    blocks = "\n\n".join(f"[CONTEXT {i + 1}]\n{c}" for i, c in enumerate(contexts))
    return f"""Break the GROUND TRUTH answer into atomic claims. For each claim,
decide whether it can be attributed to (i.e. is supported by) the CONTEXTS below.

Rules:
- Judge attribution ONLY against the contexts, not outside knowledge.
- A claim is attributed only if the contexts directly state or clearly imply it.
- Return one verdict per claim.

GROUND TRUTH:
{ground_truth}

CONTEXTS:
{blocks}
"""
