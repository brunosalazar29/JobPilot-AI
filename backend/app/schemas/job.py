from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TimestampedModel


class JobFilter(BaseModel):
    role: str | None = None
    seniority: str | None = None
    location: str | None = None
    remote: bool | None = None
    salary_min: int | None = Field(default=None, ge=0)
    technologies: list[str] = Field(default_factory=list)
    language: str | None = None


class JobCreate(BaseModel):
    source: str = "mock"
    external_id: str
    title: str
    company: str
    location: str | None = None
    seniority: str | None = None
    remote_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = "USD"
    technologies: list[str] = Field(default_factory=list)
    language_requirements: list[str] = Field(default_factory=list)
    description: str
    url: str | None = None


class JobRead(JobCreate, TimestampedModel):
    id: int

    model_config = ConfigDict(from_attributes=True)
