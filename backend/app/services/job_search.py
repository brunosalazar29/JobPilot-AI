import json
import re
import urllib.error
import urllib.request
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


class ArbeitnowJobSearchAdapter(JobSearchAdapter):
    source_name = "arbeitnow"
    endpoint = "https://www.arbeitnow.com/api/job-board-api"

    def search(self, filters: JobFilter) -> list[JobCreate]:
        request = urllib.request.Request(self.endpoint, headers={"User-Agent": "Mozilla/5.0 JobPilotAI/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Arbeitnow source failed: {exc}") from exc

        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise ValueError("Arbeitnow response did not return a jobs list")

        jobs = [self._row_to_job(row) for row in rows if isinstance(row, dict)]
        return [job for job in jobs if job_matches_filters(job, filters)]

    def _row_to_job(self, row: dict[str, Any]) -> JobCreate:
        title = str(row.get("title") or "").strip()
        company = str(row.get("company_name") or "").strip()
        description = str(row.get("description") or "").strip()
        if not title or not company or not description:
            raise ValueError("Arbeitnow row missing title/company/description")

        remote_flag = bool(row.get("remote"))
        location = str(row.get("location") or "Remote").strip()
        url = str(row.get("url") or "").strip() or None
        external_seed = str(row.get("slug") or url or f"{company}:{title}")
        technologies = normalize_values(row.get("tags") or [])

        return JobCreate(
            source=self.source_name,
            external_id=sha1(external_seed.encode("utf-8")).hexdigest(),
            title=title,
            company=company,
            location=location,
            seniority=infer_seniority_from_title(title),
            remote_type="remote" if remote_flag else "onsite",
            salary_min=None,
            salary_max=None,
            currency="USD",
            technologies=technologies,
            language_requirements=[],
            description=description,
            url=url,
        )


class RemotiveJobSearchAdapter(JobSearchAdapter):
    source_name = "remotive"
    endpoint = "https://remotive.com/api/remote-jobs?limit=100"
    technical_categories = {
        "software development",
        "devops / sysadmin",
        "qa",
        "data analysis",
    }

    def search(self, filters: JobFilter) -> list[JobCreate]:
        request = urllib.request.Request(self.endpoint, headers={"User-Agent": "Mozilla/5.0 JobPilotAI/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Remotive source failed: {exc}") from exc

        rows = payload.get("jobs", [])
        if not isinstance(rows, list):
            raise ValueError("Remotive response did not return a jobs list")

        jobs: list[JobCreate] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            category = str(row.get("category") or "").strip().lower()
            if category and category not in self.technical_categories:
                continue
            jobs.append(self._row_to_job(row))
        return [job for job in jobs if job_matches_filters(job, filters)]

    def _row_to_job(self, row: dict[str, Any]) -> JobCreate:
        title = str(row.get("title") or "").strip()
        company = str(row.get("company_name") or "").strip()
        description = str(row.get("description") or "").strip()
        if not title or not company or not description:
            raise ValueError("Remotive row missing title/company/description")

        external_seed = str(row.get("id") or row.get("url") or f"{company}:{title}")
        salary_text = str(row.get("salary") or "").strip()
        tags = normalize_values(row.get("tags") or [])
        location = str(row.get("candidate_required_location") or "Worldwide").strip()

        return JobCreate(
            source=self.source_name,
            external_id=sha1(external_seed.encode("utf-8")).hexdigest(),
            title=title,
            company=company,
            location=location,
            seniority=infer_seniority_from_title(title),
            remote_type="remote",
            salary_min=parse_salary_floor(salary_text),
            salary_max=parse_salary_ceiling(salary_text),
            currency="USD",
            technologies=tags,
            language_requirements=["english"],
            description=description,
            url=str(row.get("url") or "").strip() or None,
        )


def configured_adapters() -> list[JobSearchAdapter]:
    adapters: list[JobSearchAdapter] = []
    if settings.enable_arbeitnow_source:
        adapters.append(ArbeitnowJobSearchAdapter())
    if settings.enable_remotive_source:
        adapters.append(RemotiveJobSearchAdapter())
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


def search_jobs(db: Session, filters: JobFilter, profile: Any | None = None) -> list[Job]:
    payloads: list[JobCreate] = []
    for adapter in configured_adapters():
        try:
            payloads.extend(adapter.search(filters))
        except Exception:
            continue
    if not payloads:
        relaxed_filters = JobFilter(
            role=None,
            seniority=None,
            location=None,
            remote=None,
            salary_min=None,
            technologies=[],
            language=None,
        )
        for adapter in configured_adapters():
            try:
                payloads.extend(adapter.search(relaxed_filters))
            except Exception:
                continue
    if profile is not None:
        payloads = [payload for payload in payloads if job_matches_profile_preferences(payload, profile)]
    return upsert_jobs(db, payloads)


def build_filters_from_profile(profile: Any) -> JobFilter:
    return JobFilter(
        role=None,
        seniority=None,
        location=None,
        remote=None,
        salary_min=None,
        technologies=[],
        language=None,
    )


def normalize_values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def canonical_term(value: str) -> str:
    normalized = value.strip().lower()
    replacements = {
        "node.js": "nodejs",
        "node js": "nodejs",
        "angular.js": "angular",
        "c#": "csharp",
        "sql server": "sqlserver",
        "codeigniter 3.0": "codeigniter",
        "code igniter": "codeigniter",
        "visual basic": "vb",
        "rest api": "api",
    }
    normalized = replacements.get(normalized, normalized)
    normalized = re.sub(r"[^a-z0-9+#.]", "", normalized)
    return normalized


def expand_profile_technologies(skills: list[str]) -> list[str]:
    expanded: list[str] = []
    for skill in skills:
        normalized = skill.strip()
        if not normalized:
            continue
        expanded.append(normalized)
        canonical = canonical_term(normalized)
        if canonical == "python":
            expanded.extend(["python", "backend"])
        elif canonical == "php":
            expanded.extend(["php", "backend", "laravel"])
        elif canonical == "nodejs":
            expanded.extend(["node.js", "nodejs", "javascript", "backend"])
        elif canonical == "angular":
            expanded.extend(["angular", "frontend", "javascript"])
        elif canonical == "csharp":
            expanded.extend(["c#", ".net", "backend"])
        elif canonical == "codeigniter":
            expanded.extend(["codeigniter", "php", "backend"])
        elif canonical == "lumen":
            expanded.extend(["lumen", "php", "backend"])
        elif canonical == "sqlserver":
            expanded.extend(["sql server", "sql", "database"])
        elif canonical == "postgresql":
            expanded.extend(["postgresql", "sql", "database"])
    unique: list[str] = []
    seen: set[str] = set()
    for item in expanded:
        key = canonical_term(item)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


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
    requested = {canonical_term(item) for item in filters.technologies if canonical_term(item)}
    available = {canonical_term(item) for item in job.technologies if canonical_term(item)}
    if requested and available and not requested.intersection(available):
        return False
    return True


def fold_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower()
    replacements = str.maketrans(
        {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ü": "u",
            "ñ": "n",
        }
    )
    return lowered.translate(replacements)


def is_remote_job(job: JobCreate) -> bool:
    remote_type = fold_text(job.remote_type)
    location = fold_text(job.location)
    if remote_type in {"remote", "remoto"}:
        return True
    remote_markers = ["100% remote", "fully remote", "work from home", "remote-first", "remote", "worldwide"]
    searchable = location
    return any(marker in searchable for marker in remote_markers)


def is_peru_job(job: JobCreate) -> bool:
    searchable = fold_text(f"{job.location or ''} {job.title} {job.description}")
    peru_markers = [
        " peru",
        "peru ",
        "peru,",
        "peru.",
        "lima",
        "san isidro",
        "miraflores",
        "surco",
        "la molina",
        "callao",
    ]
    return any(marker in searchable for marker in peru_markers)


def job_matches_profile_preferences(job: JobCreate, profile: Any) -> bool:
    profile_location = fold_text(getattr(profile, "location", None))
    if "peru" in profile_location or "lima" in profile_location:
        return is_peru_job(job) or is_remote_job(job)
    return True


def parse_salary_floor(value: str | None) -> int | None:
    if not value:
        return None
    matches = re.findall(r"(\d[\d,\.]*)", value)
    if not matches:
        return None
    cleaned = matches[0].replace(",", "").replace(".", "")
    return int(cleaned) if cleaned.isdigit() else None


def parse_salary_ceiling(value: str | None) -> int | None:
    if not value:
        return None
    matches = re.findall(r"(\d[\d,\.]*)", value)
    if len(matches) < 2:
        return parse_salary_floor(value)
    cleaned = matches[1].replace(",", "").replace(".", "")
    return int(cleaned) if cleaned.isdigit() else None


def infer_seniority_from_title(title: str) -> str | None:
    lowered = title.lower()
    if any(keyword in lowered for keyword in ["lead", "staff", "principal", "head"]):
        return "lead"
    if any(keyword in lowered for keyword in ["senior", "sr"]):
        return "senior"
    if any(keyword in lowered for keyword in ["mid", "middle"]):
        return "mid"
    if any(keyword in lowered for keyword in ["junior", "jr", "intern", "trainee"]):
        return "junior"
    return None
