from pydantic import BaseModel


class RelevanceVerdict(BaseModel):
    relevant: bool  # is this context chunk useful for answering the question?
    reason: str


class RelevanceVerdictList(BaseModel):
    # One verdict per context chunk, in the SAME order the chunks were given.
    verdicts: list[RelevanceVerdict]
