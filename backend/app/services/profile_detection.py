from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ParsedResume, Profile, Resume


FIELD_LABELS = {
    "full_name": "Nombre",
    "email": "Email",
    "phone": "Teléfono",
    "location": "Ubicación",
    "linkedin_url": "LinkedIn",
    "github_url": "GitHub",
    "portfolio_url": "Portafolio",
    "experience_summary": "Experiencia",
    "skills": "Skills",
    "languages": "Idiomas",
    "seniority": "Seniority",
    "target_roles": "Roles objetivo",
    "preferred_modality": "Modalidad preferida",
    "salary_expectation": "Expectativa salarial",
}

FIELD_HELP = {
    "full_name": "Completar formularios de postulación",
    "email": "Completar formularios y contacto",
    "phone": "Completar formularios y contacto",
    "location": "Matching por ubicación",
    "linkedin_url": "Formularios y evaluación de perfil",
    "github_url": "Roles técnicos y portafolio",
    "portfolio_url": "Evidencia de trabajo",
    "experience_summary": "Matching y respuestas automáticas",
    "skills": "Matching técnico",
    "languages": "Matching por idioma",
    "seniority": "Matching por nivel",
    "target_roles": "Búsqueda de vacantes",
    "preferred_modality": "Filtrar remoto, híbrido u onsite",
    "salary_expectation": "Filtrar vacantes por compensación",
}

CRITICAL_FIELDS = ["full_name", "email", "phone", "skills", "experience_summary"]
IMPORTANT_FIELDS = ["location", "linkedin_url", "github_url", "portfolio_url", "languages", "seniority", "target_roles"]
OPTIONAL_CONTEXT_FIELDS = ["preferred_modality", "salary_expectation"]
PROFILE_FIELDS = [*CRITICAL_FIELDS, *IMPORTANT_FIELDS, *OPTIONAL_CONTEXT_FIELDS]


def get_or_create_profile(db: Session, user_id: int) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        profile = Profile(user_id=user_id, field_sources={}, missing_fields=[], recommendations=[], profile_completeness=0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def apply_cv_profile(db: Session, user_id: int, parsed_resume: ParsedResume, parsed_data: dict[str, Any]) -> Profile:
    profile = get_or_create_profile(db, user_id)
    candidate_profile = parsed_data.get("candidate_profile") or {}
    field_sources = dict(profile.field_sources or {})

    cv_fields = {
        "full_name": candidate_profile.get("full_name"),
        "email": candidate_profile.get("email"),
        "phone": candidate_profile.get("phone"),
        "location": candidate_profile.get("location"),
        "linkedin_url": candidate_profile.get("linkedin_url"),
        "github_url": candidate_profile.get("github_url"),
        "portfolio_url": candidate_profile.get("portfolio_url"),
        "experience_summary": candidate_profile.get("experience_summary"),
        "skills": parsed_resume.skills,
        "languages": parsed_resume.languages,
    }
    inferred_fields = {
        "seniority": candidate_profile.get("seniority"),
        "target_roles": candidate_profile.get("target_roles") or [],
    }

    for field, value in cv_fields.items():
        set_profile_field(profile, field_sources, field, value, "cv")
    for field, value in inferred_fields.items():
        set_profile_field(profile, field_sources, field, value, "inferred")

    refresh_profile_insights(profile, field_sources)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def apply_user_profile_update(db: Session, profile: Profile, updates: dict[str, Any]) -> Profile:
    field_sources = dict(profile.field_sources or {})
    for field, value in updates.items():
        if field not in PROFILE_FIELDS and field != "salary_currency":
            continue
        setattr(profile, field, normalize_value(value))
        if field != "salary_currency":
            field_sources[field] = "user_input"
    refresh_profile_insights(profile, field_sources)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def set_profile_field(profile: Profile, field_sources: dict[str, str], field: str, value: Any, source: str) -> None:
    value = normalize_value(value)
    if is_empty(value):
        return
    if field_sources.get(field) == "user_input":
        return

    current_value = getattr(profile, field, None)
    if isinstance(value, list) and isinstance(current_value, list):
        merged = merge_unique(current_value, value)
        setattr(profile, field, merged)
    else:
        setattr(profile, field, value)
    field_sources[field] = source


def refresh_profile_insights(profile: Profile, field_sources: dict[str, str] | None = None) -> None:
    profile.skills = profile.skills or []
    profile.languages = profile.languages or []
    profile.target_roles = profile.target_roles or []
    profile.salary_currency = profile.salary_currency or "USD"
    sources = field_sources or dict(profile.field_sources or {})
    missing = [field for field in PROFILE_FIELDS if is_empty(getattr(profile, field, None))]
    profile.field_sources = sources
    profile.missing_fields = missing
    profile.recommendations = build_recommendations(missing)
    profile.profile_completeness = calculate_completeness(profile)


def build_detected_profile(db: Session, user_id: int) -> dict[str, Any]:
    profile = get_or_create_profile(db, user_id)
    refresh_profile_insights(profile)
    db.add(profile)
    db.commit()
    db.refresh(profile)

    latest_resume = db.scalar(
        select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
    )
    resume_payload = None
    if latest_resume is not None:
        resume_payload = {
            "id": latest_resume.id,
            "filename": latest_resume.original_filename,
            "status": latest_resume.status,
            "parsed_at": latest_resume.parsed_at,
            "error_message": latest_resume.error_message,
        }

    return {
        "profile": profile,
        "fields": [build_field_payload(profile, field) for field in PROFILE_FIELDS],
        "missing_fields": profile.missing_fields or [],
        "recommendations": profile.recommendations or [],
        "completeness": profile.profile_completeness or 0,
        "latest_resume": resume_payload,
    }


def build_field_payload(profile: Profile, field: str) -> dict[str, Any]:
    value = getattr(profile, field, None)
    source = (profile.field_sources or {}).get(field, "missing" if is_empty(value) else "unknown")
    if is_empty(value):
        status = "missing"
    elif source == "inferred":
        status = "inferred"
    elif source == "cv":
        status = "detected"
    elif source == "user_input":
        status = "user_input"
    else:
        status = "pending_confirmation"

    return {
        "key": field,
        "label": FIELD_LABELS[field],
        "value": value,
        "source": source,
        "status": status,
        "useful_for": FIELD_HELP[field],
        "needs_confirmation": source in {"cv", "inferred"},
    }


def build_recommendations(missing: list[str]) -> list[dict[str, str]]:
    recommendations = []
    for field in missing:
        severity = "critical" if field in CRITICAL_FIELDS else "optional"
        recommendations.append(
            {
                "field": field,
                "label": FIELD_LABELS[field],
                "severity": severity,
                "message": f"No se detectó {FIELD_LABELS[field].lower()}.",
                "reason": FIELD_HELP[field],
            }
        )
    return recommendations


def calculate_completeness(profile: Profile) -> int:
    weights = {
        "full_name": 10,
        "email": 10,
        "phone": 8,
        "location": 7,
        "linkedin_url": 6,
        "github_url": 6,
        "portfolio_url": 4,
        "experience_summary": 12,
        "skills": 15,
        "languages": 6,
        "seniority": 6,
        "target_roles": 6,
        "preferred_modality": 2,
        "salary_expectation": 2,
    }
    total = sum(weights.values())
    score = sum(weight for field, weight in weights.items() if not is_empty(getattr(profile, field, None)))
    return round((score / total) * 100)


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in {"nada", "ninguno", "none", "null", "n/a", "na", "-", "sin dato"}:
            return None
        return value or None
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return value


def is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    seen = set()
    merged = []
    for value in [*existing, *incoming]:
        normalized = value.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            merged.append(value.strip())
    return merged
