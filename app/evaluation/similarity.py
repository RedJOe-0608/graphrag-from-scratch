import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Cosine similarity of two vectors, in pure Python (no numpy dependency).
    Returns 0.0 if either vector is all-zeros (undefined direction).
    """
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
