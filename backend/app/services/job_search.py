import json
import re
from hashlib import sha1
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Job
from app.schemas.job import JobCreate, JobFilter


class JobSearchAdapter:
    source_name = "base"

    def search(self, filters: JobFilter) -> list[JobCreate]:
        raise NotImplementedError


class MockJobSearchAdapter(JobSearchAdapter):
    source_name = "mock"

    def search(self, filters: JobFilter) -> list[JobCreate]:
        role = filters.role or "Software Engineer"
        seniority = filters.seniority or "mid"
        location = filters.location or "Remote LATAM"
        remote_type = "remote" if filters.remote is not False else "onsite"
        technologies = filters.technologies or ["python", "typescript", "sql server", "react"]
        language = filters.language or "english"
        salary_floor = filters.salary_min or 3500

        templates = [
            ("Northstar Labs", "Build internal automation workflows and data-backed hiring tools."),
            ("Andes Digital", "Own product features across API, background jobs and dashboard UX."),
            ("CloudBridge Systems", "Integrate third-party platforms, queues and reporting workflows."),
            ("TalentOps AI", "Create applicant tracking automations with human review checkpoints."),
        ]

        jobs: list[JobCreate] = []
        for index, (company, description) in enumerate(templates, start=1):
            title = f"{seniority.title()} {role}"
            external_source = f"{self.source_name}:{company}:{title}:{','.join(technologies)}"
            external_id = sha1(external_source.encode("utf-8")).hexdigest()
            jobs.append(
                JobCreate(
                    source=self.source_name,
                    external_id=external_id,
                    title=title,
                    company=company,
                    location=location,
                    seniority=seniority,
                    remote_type=remote_type,
                    salary_min=salary_floor + (index - 1) * 500,
                    salary_max=salary_floor + 2500 + (index - 1) * 700,
                    currency="USD",
                    technologies=technologies,
                    language_requirements=[language],
                    description=f"{description} Stack esperado: {', '.join(technologies)}. Modalidad: {remote_type}.",
                    url=f"https://jobs.example.com/{external_id}",
                )
            )
        return jobs


class LocalJsonJobSearchAdapter(JobSearchAdapter):
    source_name = "local_json"

    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def search(self, filters: JobFilter) -> list[JobCreate]:
        if not self.path.exists():
            raise FileNotFoundError(f"Configured job source file does not exist: {self.path}")
        with self.path.open("r", encoding="utf-8") as source_file:
            data = json.load(source_file)
        rows = data.get("jobs", data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError("Job source file must contain a list or an object with a jobs list")

        jobs = [self._row_to_job(row) for row in rows if isinstance(row, dict)]
        return [job for job in jobs if job_matches_filters(job, filters)]

    def _row_to_job(self, row: dict[str, Any]) -> JobCreate:
        title = str(row.get("title") or row.get("position") or "").strip()
        company = str(row.get("company") or "").strip()
        description = str(row.get("description") or "").strip()
        if not title or not company or not description:
            raise ValueError("Each imported job needs title, company and description")
        source = str(row.get("source") or self.source_name)
        external_seed = str(row.get("external_id") or row.get("url") or f"{company}:{title}:{description[:120]}")
        return JobCreate(
            source=source,
            external_id=sha1(external_seed.encode("utf-8")).hexdigest(),
            title=title,
            company=company,
            location=row.get("location"),
            seniority=row.get("seniority"),
            remote_type=row.get("remote_type") or row.get("modality"),
            salary_min=row.get("salary_min"),
            salary_max=row.get("salary_max"),
            currency=row.get("currency") or "USD",
            technologies=normalize_values(row.get("technologies") or row.get("skills") or []),
            language_requirements=normalize_values(row.get("language_requirements") or row.get("languages") or []),
            description=description,
            url=row.get("url"),
        )


def configured_adapters() -> list[JobSearchAdapter]:
    adapters: list[JobSearchAdapter] = []
    if settings.job_source_file:
        adapters.append(LocalJsonJobSearchAdapter(settings.job_source_file))
    if settings.enable_mock_jobs:
        adapters.append(MockJobSearchAdapter())
    return adapters


def upsert_jobs(db: Session, job_payloads: list[JobCreate]) -> list[Job]:
    jobs: list[Job] = []
    for payload in job_payloads:
        job = db.scalar(select(Job).where(Job.source == payload.source, Job.external_id == payload.external_id))
        data: dict[str, Any] = payload.model_dump()
        if job is None:
            job = Job(**data)
            db.add(job)
        else:
            for key, value in data.items():
                setattr(job, key, value)
        jobs.append(job)
    db.commit()
    for job in jobs:
        db.refresh(job)
    return jobs


def search_jobs(db: Session, filters: JobFilter) -> list[Job]:
    payloads: list[JobCreate] = []
    for adapter in configured_adapters():
        payloads.extend(adapter.search(filters))
    return upsert_jobs(db, payloads)


def build_filters_from_profile(profile: Any) -> JobFilter:
    target_roles = profile.target_roles or []
    role = target_roles[0] if target_roles else None
    return JobFilter(
        role=role,
        seniority=profile.seniority,
        location=profile.location,
        remote=(profile.preferred_modality or "").lower() == "remote" if profile.preferred_modality else None,
        salary_min=profile.salary_expectation,
        technologies=profile.skills or [],
        language=(profile.languages or [None])[0],
    )


def normalize_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def job_matches_filters(job: JobCreate, filters: JobFilter) -> bool:
    role = (filters.role or "").lower()
    if role and role not in f"{job.title} {job.description}".lower():
        job_words = set(re.findall(r"[a-zA-Z+#.]{3,}", f"{job.title} {job.description}".lower()))
        role_words = set(re.findall(r"[a-zA-Z+#.]{3,}", role))
        if not role_words.intersection(job_words):
            return False
    if filters.remote is True and (job.remote_type or "").lower() not in {"remote", "remoto"}:
        return False
    if filters.salary_min and job.salary_max and job.salary_max < filters.salary_min:
        return False
    requested = {item.lower() for item in filters.technologies}
    available = {item.lower() for item in job.technologies}
    if requested and available and not requested.intersection(available):
        return False
    return True
