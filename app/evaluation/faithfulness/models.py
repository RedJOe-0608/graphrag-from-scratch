from pydantic import BaseModel


class ClaimVerdict(BaseModel):
    claim: str # the atomic statement being judged.
    supported: bool # the actual judgement: is this claim backed by the context?
    reason: str # the LLM justification


class VerdictList(BaseModel):
    verdicts: list[ClaimVerdict]

class ClaimList(BaseModel):
    claims: list[str]
