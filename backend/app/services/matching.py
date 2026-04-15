import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, JobMatch, ParsedResume, Profile, Resume


def run_matching_for_user(
    db: Session,
    user_id: int,
    resume_id: int | None = None,
    job_ids: list[int] | None = None,
) -> list[JobMatch]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    parsed_resume = get_parsed_resume(db, user_id, resume_id)
    query = select(Job)
    if job_ids:
        query = query.where(Job.id.in_(job_ids))
    jobs = db.scalars(query.order_by(Job.created_at.desc())).all()

    matches = []
    for job in jobs:
        result = calculate_match(profile, parsed_resume, job)
        existing = db.scalar(select(JobMatch).where(JobMatch.user_id == user_id, JobMatch.job_id == job.id))
        if existing is None:
            existing = JobMatch(user_id=user_id, job_id=job.id)
            db.add(existing)
        existing.resume_id = parsed_resume.resume_id if parsed_resume else resume_id
        existing.score = result["score"]
        existing.summary = result["summary"]
        existing.criteria = result["criteria"]
        existing.missing_keywords = result["missing_keywords"]
        matches.append(existing)

    db.commit()
    for match in matches:
        db.refresh(match)
    return matches


def get_parsed_resume(db: Session, user_id: int, resume_id: int | None = None) -> ParsedResume | None:
    query = select(ParsedResume).join(Resume).where(Resume.user_id == user_id)
    if resume_id:
        query = query.where(Resume.id == resume_id)
    return db.scalar(query.order_by(ParsedResume.created_at.desc()))


def calculate_match(profile: Profile | None, parsed_resume: ParsedResume | None, job: Job) -> dict[str, Any]:
    profile_skills = set(normalize_list(profile.skills if profile else []))
    resume_skills = set(normalize_list(parsed_resume.skills if parsed_resume else []))
    candidate_skills = profile_skills | resume_skills
    job_skills = set(normalize_list(job.technologies or []))
    matched_skills = sorted(candidate_skills & job_skills)
    missing_skills = sorted(job_skills - candidate_skills)

    criteria = {
        "skills": weighted_ratio(len(matched_skills), len(job_skills), 45),
        "seniority": seniority_score(profile, job) * 15,
        "language": language_score(profile, parsed_resume, job) * 15,
        "location": location_score(profile, job) * 10,
        "modality": modality_score(profile, job) * 10,
        "salary": salary_score(profile, job) * 5,
    }
    score = round(sum(criteria.values()), 2)
    summary = (
        f"{score:.0f}% compatible. Coinciden {len(matched_skills)} skills clave"
        f" ({', '.join(matched_skills[:5]) or 'sin coincidencias directas'})."
    )
    if missing_skills:
        summary += f" Faltantes principales: {', '.join(missing_skills[:5])}."

    return {"score": score, "criteria": criteria, "missing_keywords": missing_skills, "summary": summary}


def normalize_list(values: list[str]) -> list[str]:
    return [value.strip().lower() for value in values if value and value.strip()]


def weighted_ratio(matches: int, total: int, weight: int) -> float:
    if total == 0:
        return float(weight)
    return round((matches / total) * weight, 2)


def seniority_score(profile: Profile | None, job: Job) -> float:
    if not job.seniority:
        return 1.0
    if profile and profile.seniority and profile.seniority.lower() == job.seniority.lower():
        return 1.0
    summary = (profile.experience_summary or "").lower() if profile else ""
    if job.seniority.lower() in summary:
        return 1.0
    seniority_keywords = {"junior": "junior", "mid": "mid", "senior": "senior", "lead": "lead"}
    return 0.7 if any(keyword in summary for keyword in seniority_keywords.values()) else 0.5


def language_score(profile: Profile | None, parsed_resume: ParsedResume | None, job: Job) -> float:
    required = set(normalize_list(job.language_requirements or []))
    if not required:
        return 1.0
    profile_languages = set(normalize_list(profile.languages if profile else []))
    resume_languages = set(normalize_list(parsed_resume.languages if parsed_resume else []))
    available = profile_languages | resume_languages
    return 1.0 if required & available else 0.35


def location_score(profile: Profile | None, job: Job) -> float:
    if (job.remote_type or "").lower() == "remote":
        return 1.0
    if not profile or not profile.location or not job.location:
        return 0.5
    return 1.0 if profile.location.lower() in job.location.lower() else 0.4


def modality_score(profile: Profile | None, job: Job) -> float:
    if not profile or not profile.preferred_modality or not job.remote_type:
        return 0.7
    return 1.0 if profile.preferred_modality.lower() in job.remote_type.lower() else 0.35


def salary_score(profile: Profile | None, job: Job) -> float:
    if not profile or not profile.salary_expectation or not job.salary_max:
        return 0.75
    return 1.0 if job.salary_max >= profile.salary_expectation else 0.25


def extract_profile_keywords(profile: Profile | None) -> set[str]:
    if not profile or not profile.experience_summary:
        return set()
    return {word for word in re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", profile.experience_summary.lower())}
