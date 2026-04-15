from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(50), default="uploaded", index=True, nullable=False)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="resumes")
    parsed_resume: Mapped["ParsedResume"] = relationship(back_populates="resume", uselist=False, cascade="all, delete-orphan")
    generated_documents: Mapped[list["GeneratedDocument"]] = relationship(back_populates="resume")
    applications: Mapped[list["Application"]] = relationship(back_populates="resume")


class ParsedResume(TimestampMixin, Base):
    __tablename__ = "parsed_resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    work_experience: Mapped[list[dict]] = mapped_column(JSON, default=list)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    education: Mapped[list[dict]] = mapped_column(JSON, default=list)
    certifications: Mapped[list[str]] = mapped_column(JSON, default=list)
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    extra_data: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    resume: Mapped["Resume"] = relationship(back_populates="parsed_resume")
