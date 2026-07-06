from pydantic import BaseModel


class AttributionVerdict(BaseModel):
    claim: str  # an atomic claim taken from the ground-truth answer
    attributed: bool  # can this claim be supported by the retrieved context?
    reason: str


class AttributionVerdictList(BaseModel):
    verdicts: list[AttributionVerdict]
