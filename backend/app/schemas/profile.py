from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import TimestampedModel


class ProfileBase(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    experience_summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    seniority: str | None = Field(default=None, max_length=80)
    target_roles: list[str] = Field(default_factory=list)
    preferred_modality: str | None = Field(default=None, max_length=80)
    salary_expectation: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default="USD", max_length=10)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    experience_summary: str | None = None
    skills: list[str] | None = None
    languages: list[str] | None = None
    seniority: str | None = Field(default=None, max_length=80)
    target_roles: list[str] | None = None
    preferred_modality: str | None = Field(default=None, max_length=80)
    salary_expectation: int | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, max_length=10)


class ProfileRead(ProfileBase, TimestampedModel):
    id: int
    user_id: int
    field_sources: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    profile_completeness: int = 0

    model_config = ConfigDict(from_attributes=True)


class DetectedProfileField(BaseModel):
    key: str
    label: str
    value: Any = None
    source: str
    status: str
    useful_for: str
    needs_confirmation: bool = False


class DetectedProfileResponse(BaseModel):
    profile: ProfileRead
    fields: list[DetectedProfileField]
    missing_fields: list[str]
    recommendations: list[dict[str, Any]]
    completeness: int
    latest_resume: dict[str, Any] | None = None
