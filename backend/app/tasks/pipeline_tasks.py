from datetime import UTC, datetime

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Application, Job, ParsedResume, Resume, TaskRun
from app.services.cv_parser import parse_resume_file
from app.services.generation import generate_application_responses
from app.services.job_search import build_filters_from_profile, configured_adapters, search_jobs
from app.services.matching import run_matching_for_user
from app.services.profile_detection import apply_cv_profile
from app.services.task_logger import append_task_log, log_activity, mark_task_failed, mark_task_running, mark_task_success


@celery_app.task(name="jobpilot.cv_pipeline")
def cv_pipeline_task(task_run_id: int, resume_id: int) -> dict:
    db = SessionLocal()
    try:
        task_run = db.get(TaskRun, task_run_id)
        resume = db.get(Resume, resume_id)
        if task_run is None or resume is None:
            raise ValueError("Task run or resume not found")

        mark_task_running(db, task_run, progress=5)
        append_task_log(db, task_run, "parse_cv started", data={"resume_id": resume.id})
        resume.status = "parsing"
        db.add(resume)
        db.commit()

        parsed_data = parse_resume_file(resume.storage_path)
        parsed = resume.parsed_resume or ParsedResume(resume_id=resume.id)
        parsed.raw_text = parsed_data["raw_text"]
        parsed.work_experience = parsed_data["work_experience"]
        parsed.skills = parsed_data["skills"]
        parsed.education = parsed_data["education"]
        parsed.certifications = parsed_data["certifications"]
        parsed.languages = parsed_data["languages"]
        parsed.extra_data = parsed_data["metadata"]
        db.add(parsed)
        db.flush()

        append_task_log(db, task_run, "infer_profile started")
        profile = apply_cv_profile(db, resume.user_id, parsed, parsed_data)
        resume.status = "parsed"
        resume.parsed_at = datetime.now(UTC)
        resume.error_message = None
        db.add(resume)
        db.commit()

        adapters = configured_adapters()
        append_task_log(
            db,
            task_run,
            "collect_jobs started" if adapters else "collect_jobs skipped: no real job sources configured",
            data={"sources": [adapter.source_name for adapter in adapters]},
        )
        filters = build_filters_from_profile(profile)
        jobs = search_jobs(db, filters) if adapters else []

        append_task_log(db, task_run, "match_jobs started", data={"job_count": len(jobs)})
        matches = run_matching_for_user(
            db,
            user_id=resume.user_id,
            resume_id=resume.id,
            job_ids=[job.id for job in jobs],
        ) if jobs else []

        append_task_log(
            db,
            task_run,
            "create_queue_items started",
            data={"match_count": len(matches), "threshold": settings.application_match_threshold},
        )
        created_applications = []
        for match in matches:
            if match.score < settings.application_match_threshold:
                continue
            job = db.get(Job, match.job_id)
            if job is None:
                continue
            existing = db.scalar(
                select(Application).where(Application.user_id == resume.user_id, Application.job_id == job.id)
            )
            if existing is not None:
                if existing.status in {"found", "matched", "pending"}:
                    existing.status = "matched"
                    existing.score = match.score
                    existing.resume_id = resume.id
                    db.add(existing)
                    created_applications.append(existing)
                continue
            application = Application(
                user_id=resume.user_id,
                job_id=job.id,
                resume_id=resume.id,
                company=job.company,
                position=job.title,
                url=job.url,
                score=match.score,
                status="matched",
                generated_responses=generate_application_responses(profile, job, parsed),
                logs=[
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "level": "info",
                        "message": "Queue item created from CV pipeline",
                        "score": match.score,
                    }
                ],
            )
            db.add(application)
            created_applications.append(application)

        db.commit()
        for application in created_applications:
            db.refresh(application)

        result = {
            "resume_id": resume.id,
            "profile_completeness": profile.profile_completeness,
            "missing_fields": profile.missing_fields,
            "jobs_collected": len(jobs),
            "matches_created": len(matches),
            "queue_items_created": len(created_applications),
            "sources": [adapter.source_name for adapter in adapters],
        }
        log_activity(db, resume.user_id, "resume", "cv_pipeline_completed", resume.original_filename, resume.id, result)
        mark_task_success(db, task_run, result=result)
        return result
    except Exception as exc:
        db.rollback()
        task_run = db.get(TaskRun, task_run_id)
        resume = db.get(Resume, resume_id)
        if resume is not None:
            resume.status = "failed"
            resume.error_message = str(exc)
            db.add(resume)
            db.commit()
        if task_run is not None:
            mark_task_failed(db, task_run, str(exc))
        raise
    finally:
        db.close()
