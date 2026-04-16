import asyncio
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Application, Profile, Resume, TaskRun
from app.services.automation import prepare_application_form
from app.services.search_run import mark_search_completed, mark_search_stage, should_continue_search
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
        if not should_continue_search(db, application.user_id):
            application.status = "cancelled"
            application.logs = [
                *(application.logs or []),
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "level": "warning",
                    "message": "Search run stopped by user",
                },
            ]
            db.add(application)
            db.commit()
            mark_task_success(db, task_run, result={"application_id": application.id, "stopped": True})
            return {"application_id": application.id, "stopped": True}

        mark_task_running(db, task_run, progress=15)
        append_task_log(db, task_run, "Preparing web application form")
        mark_search_stage(
            db,
            application.user_id,
            "Preparando postulacion",
            f"Preparando postulacion para {application.company}.",
        )
        application.status = "preparing"
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

        domain = urlparse(application.url).netloc.lower() if application.url else ""
        evidence_dir = Path("/app/storage/automation") / str(application.user_id) / str(application.id)
        append_task_log(db, task_run, f"Applying to {application.company} at {domain or 'unknown domain'}")
        mark_search_stage(
            db,
            application.user_id,
            "Intentando postular",
            f"Llenando formulario en {domain or application.company}.",
        )
        application.logs = [
            *(application.logs or []),
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": "info",
                "message": f"Preparing application for {application.company}",
                "domain": domain,
            },
        ]
        application.status = "applying"
        db.add(application)
        db.commit()

        result = asyncio.run(
            prepare_application_form(
                url=application.url,
                profile_data=profile_data,
                resume_path=resume.storage_path if resume else None,
                evidence_dir=str(evidence_dir),
            )
        )
        final_status = result.get("status", "needs_manual_action")
        if result.get("final_url"):
            application.url = result["final_url"]
        if not should_continue_search(db, application.user_id):
            final_status = "cancelled"
            result["error"] = "Search run stopped by user"
            result["logs"] = [
                *(result.get("logs") or []),
                {"timestamp": datetime.now(UTC).isoformat(), "level": "warning", "message": "Search run stopped by user"},
            ]
        application.status = final_status
        if final_status == "applied":
            application.applied_at = datetime.now(UTC)
        application.logs = [*(application.logs or []), *(result.get("logs") or [])]
        application.errors = result.get("error")
        if result.get("screenshot_path"):
            application.document_refs = [
                *(application.document_refs or []),
                {
                    "type": "automation_screenshot",
                    "path": result.get("screenshot_path"),
                    "domain": result.get("domain") or domain,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            ]
        append_task_log(
            db,
            task_run,
            f"Application attempt finished with status {final_status}",
            data={
                "application_id": application.id,
                "domain": result.get("domain") or domain,
                "screenshot_path": result.get("screenshot_path"),
                "error": result.get("error"),
            },
        )
        db.add(application)
        db.commit()
        if should_continue_search(db, application.user_id):
            mark_search_completed(
                db,
                application.user_id,
                f"Ultimo intento procesado: {application.company} quedo en {final_status}.",
            )

        log_activity(
            db,
            application.user_id,
            "application",
            "attempted",
            f"Application attempt finished with status {final_status}",
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
