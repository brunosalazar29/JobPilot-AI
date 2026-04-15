from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), index=True)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"))
    company: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    position: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    url: Mapped[str | None] = mapped_column(String(1500))
    score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)
    generated_responses: Mapped[dict] = mapped_column(JSON, default=dict)
    document_refs: Mapped[list[dict]] = mapped_column(JSON, default=list)
    logs: Mapped[list[dict]] = mapped_column(JSON, default=list)
    errors: Mapped[str | None] = mapped_column(Text)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    resume: Mapped["Resume"] = relationship(back_populates="applications")
    generated_documents: Mapped[list["GeneratedDocument"]] = relationship(back_populates="application")


class GeneratedDocument(TimestampMixin, Base):
    __tablename__ = "generated_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id"))
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"))
    application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"))
    kind: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="generated_documents")
    resume: Mapped["Resume"] = relationship(back_populates="generated_documents")
    job: Mapped["Job"] = relationship(back_populates="generated_documents")
    application: Mapped["Application"] = relationship(back_populates="generated_documents")
