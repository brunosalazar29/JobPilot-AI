from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import JsonDict, TimestampedModel


class ParsedResumeRead(TimestampedModel):
    id: int
    resume_id: int
    raw_text: str
    work_experience: list[JsonDict] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[JsonDict] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    extra_data: JsonDict = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("work_experience", "education", mode="before")
    @classmethod
    def normalize_structured_items(cls, value: object) -> list[JsonDict]:
        if not isinstance(value, list):
            return []
        normalized: list[JsonDict] = []
        for item in value:
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, str) and item.strip():
                normalized.append({"text": item.strip()})
        return normalized


class ResumeRead(TimestampedModel):
    id: int
    user_id: int
    original_filename: str
    storage_path: str
    content_type: str | None
    status: str
    parsed_at: datetime | None
    error_message: str | None
    parsed_resume: ParsedResumeRead | None = None

    model_config = ConfigDict(from_attributes=True)


class GeneratedDocumentCreate(BaseModel):
    kind: str = Field(default="cover_letter", max_length=80)
    job_id: int | None = None
    resume_id: int | None = None
    application_id: int | None = None


class GeneratedDocumentRead(TimestampedModel):
    id: int
    user_id: int
    resume_id: int | None
    job_id: int | None
    application_id: int | None
    kind: str
    title: str
    content: str
    status: str

    model_config = ConfigDict(from_attributes=True)
