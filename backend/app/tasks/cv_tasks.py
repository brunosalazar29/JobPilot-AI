from datetime import UTC, datetime

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import ParsedResume, Resume, TaskRun
from app.services.cv_parser import parse_resume_file
from app.services.profile_detection import apply_cv_profile
from app.services.task_logger import append_task_log, log_activity, mark_task_failed, mark_task_running, mark_task_success


@celery_app.task(name="jobpilot.parse_resume")
def parse_resume_task(task_run_id: int, resume_id: int) -> dict:
    db = SessionLocal()
    try:
        task_run = db.get(TaskRun, task_run_id)
        resume = db.get(Resume, resume_id)
        if task_run is None or resume is None:
            raise ValueError("Task run or resume not found")

        mark_task_running(db, task_run, progress=10)
        resume.status = "parsing"
        db.add(resume)
        db.commit()
        append_task_log(db, task_run, "Started resume parsing")

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

        profile = apply_cv_profile(db, resume.user_id, parsed, parsed_data)

        resume.status = "parsed"
        resume.parsed_at = datetime.now(UTC)
        resume.error_message = None
        db.add(resume)
        db.commit()

        log_activity(
            db,
            user_id=resume.user_id,
            entity_type="resume",
            entity_id=resume.id,
            action="parsed",
            message=f"Parsed resume {resume.original_filename}",
        )
        result = {
            "resume_id": resume.id,
            "parsed_resume_id": parsed.id,
            "skills": parsed.skills,
            "profile_completeness": profile.profile_completeness,
            "missing_fields": profile.missing_fields,
        }
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
