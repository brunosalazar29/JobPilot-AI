from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import JsonDict, TimestampedModel
from app.schemas.job import JobRead


class MatchRunRequest(BaseModel):
    resume_id: int | None = None
    job_ids: list[int] = Field(default_factory=list)


class JobMatchRead(TimestampedModel):
    id: int
    user_id: int
    job_id: int
    resume_id: int | None
    score: float
    summary: str | None
    criteria: JsonDict = Field(default_factory=dict)
    missing_keywords: list[str] = Field(default_factory=list)
    job: JobRead | None = None

    model_config = ConfigDict(from_attributes=True)
