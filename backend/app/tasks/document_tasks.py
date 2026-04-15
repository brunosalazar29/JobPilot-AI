from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import Application, GeneratedDocument, Job, Profile, TaskRun
from app.services.generation import generate_document_content
from app.services.matching import get_parsed_resume
from app.services.task_logger import append_task_log, log_activity, mark_task_failed, mark_task_running, mark_task_success


@celery_app.task(name="jobpilot.generate_document")
def generate_document_task(
    task_run_id: int,
    user_id: int,
    kind: str,
    job_id: int | None = None,
    resume_id: int | None = None,
    application_id: int | None = None,
) -> dict:
    db = SessionLocal()
    try:
        task_run = db.get(TaskRun, task_run_id)
        if task_run is None:
            raise ValueError("Task run not found")
        mark_task_running(db, task_run, progress=25)
        append_task_log(db, task_run, f"Generating document: {kind}")

        profile = db.scalar(select(Profile).where(Profile.user_id == user_id))
        job = db.get(Job, job_id) if job_id else None
        parsed_resume = get_parsed_resume(db, user_id, resume_id)
        title, content = generate_document_content(kind, profile, job, parsed_resume)

        document = GeneratedDocument(
            user_id=user_id,
            resume_id=resume_id,
            job_id=job_id,
            application_id=application_id,
            kind=kind,
            title=title,
            content=content,
            status="draft",
        )
        db.add(document)
        db.flush()

        if application_id:
            application = db.get(Application, application_id)
            if application is not None:
                application.document_refs = [
                    *(application.document_refs or []),
                    {"generated_document_id": document.id, "kind": kind, "title": title},
                ]
                db.add(application)

        db.commit()
        db.refresh(document)
        result = {"generated_document_id": document.id, "kind": document.kind, "title": document.title}
        log_activity(db, user_id, "generated_document", "created", title, entity_id=document.id, extra_data=result)
        mark_task_success(db, task_run, result=result)
        return result
    except Exception as exc:
        db.rollback()
        task_run = db.get(TaskRun, task_run_id)
        if task_run is not None:
            mark_task_failed(db, task_run, str(exc))
        raise
    finally:
        db.close()
