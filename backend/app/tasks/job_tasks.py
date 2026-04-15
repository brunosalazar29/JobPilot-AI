from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import TaskRun
from app.schemas.job import JobFilter
from app.services.job_search import configured_adapters, search_jobs
from app.services.matching import run_matching_for_user
from app.services.task_logger import append_task_log, log_activity, mark_task_failed, mark_task_running, mark_task_success


@celery_app.task(name="jobpilot.search_jobs")
def search_jobs_task(task_run_id: int, user_id: int, filters: dict) -> dict:
    db = SessionLocal()
    try:
        task_run = db.get(TaskRun, task_run_id)
        if task_run is None:
            raise ValueError("Task run not found")
        mark_task_running(db, task_run, progress=15)
        adapters = configured_adapters()
        append_task_log(
            db,
            task_run,
            "Searching jobs through configured sources" if adapters else "No job sources configured",
            data={"filters": filters, "sources": [adapter.source_name for adapter in adapters]},
        )

        jobs = search_jobs(db, JobFilter(**filters))
        result = {"job_ids": [job.id for job in jobs], "count": len(jobs)}
        log_activity(db, user_id, "job", "searched", f"Found {len(jobs)} jobs", extra_data=result)
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


@celery_app.task(name="jobpilot.run_matching")
def run_matching_task(task_run_id: int, user_id: int, resume_id: int | None = None, job_ids: list[int] | None = None) -> dict:
    db = SessionLocal()
    try:
        task_run = db.get(TaskRun, task_run_id)
        if task_run is None:
            raise ValueError("Task run not found")
        mark_task_running(db, task_run, progress=20)
        append_task_log(db, task_run, "Calculating job matches")

        matches = run_matching_for_user(db, user_id=user_id, resume_id=resume_id, job_ids=job_ids or [])
        result = {"match_ids": [match.id for match in matches], "count": len(matches)}
        log_activity(db, user_id, "job_match", "matched", f"Calculated {len(matches)} matches", extra_data=result)
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
