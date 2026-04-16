from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import JsonDict, TimestampedModel
from app.schemas.job import JobRead


APPLICATION_STATUSES = {
    "found",
    "matched",
    "queued",
    "preparing",
    "applying",
    "applied",
    "failed",
    "needs_manual_action",
    "paused",
    "cancelled",
}


class ApplicationCreate(BaseModel):
    job_id: int | None = None
    resume_id: int | None = None
    company: str | None = None
    position: str | None = None
    url: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: str


class ApplicationRead(TimestampedModel):
    id: int
    user_id: int
    job_id: int | None
    resume_id: int | None
    company: str
    position: str
    url: str | None
    score: float | None
    status: str
    generated_responses: JsonDict = Field(default_factory=dict)
    document_refs: list[JsonDict] = Field(default_factory=list)
    logs: list[JsonDict] = Field(default_factory=list)
    errors: str | None
    applied_at: datetime | None
    job: JobRead | None = None

    model_config = ConfigDict(from_attributes=True)
