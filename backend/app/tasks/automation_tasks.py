import asyncio

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Application, Profile, Resume, TaskRun
from app.services.automation import prepare_application_form
from app.services.task_logger import append_task_log, log_activity, mark_task_failed, mark_task_running, mark_task_success


@celery_app.task(name="jobpilot.prepare_application_form")
def prepare_application_form_task(task_run_id: int, application_id: int) -> dict:
    db = SessionLocal()
    try:
        task_run = db.get(TaskRun, task_run_id)
        application = db.get(Application, application_id)
        if task_run is None or application is None:
            raise ValueError("Task run or application not found")
        if not application.url:
            raise ValueError("Application URL is required")

        mark_task_running(db, task_run, progress=15)
        append_task_log(db, task_run, "Preparing web application form")
        application.status = "running"
        db.add(application)
        db.commit()

        profile = db.scalar(select(Profile).where(Profile.user_id == application.user_id))
        resume = db.get(Resume, application.resume_id) if application.resume_id else None
        profile_data = {
            "full_name": profile.full_name if profile else None,
            "email": profile.email if profile else None,
            "phone": profile.phone if profile else None,
            "location": profile.location if profile else None,
            "linkedin_url": profile.linkedin_url if profile else None,
            "github_url": profile.github_url if profile else None,
            "portfolio_url": profile.portfolio_url if profile else None,
        }

        result = asyncio.run(
            prepare_application_form(
                url=application.url,
                profile_data=profile_data,
                resume_path=resume.storage_path if resume else None,
            )
        )
        application.status = result.get("status", "ready_for_review")
        application.logs = [*(application.logs or []), *(result.get("logs") or [])]
        application.errors = result.get("error")
        db.add(application)
        db.commit()

        log_activity(
            db,
            application.user_id,
            "application",
            "prepared",
            "Application form prepared for manual review",
            entity_id=application.id,
            extra_data={"status": application.status},
        )
        mark_task_success(db, task_run, result=result)
        return result
    except Exception as exc:
        db.rollback()
        task_run = db.get(TaskRun, task_run_id)
        application = db.get(Application, application_id)
        if application is not None:
            application.status = "failed"
            application.errors = str(exc)
            db.add(application)
            db.commit()
        if task_run is not None:
            mark_task_failed(db, task_run, str(exc))
        raise
    finally:
        db.close()
