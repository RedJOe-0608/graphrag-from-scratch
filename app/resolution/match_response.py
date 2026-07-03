from typing import Literal

from pydantic import BaseModel, create_model


def build_match_response(candidate_ids: list[str]) -> type[BaseModel]:
    """
    Build a response model whose `match` field is constrained to exactly the
    given candidate ids plus the sentinel "none". Constrained decoding then makes
    it structurally impossible for the LLM to return an id that isn't a real
    candidate (no uuid-transcription errors).
    """
    return create_model(
        "MatchResponse",
        match=(Literal[tuple(candidate_ids + ["none"])], ...),
    )
