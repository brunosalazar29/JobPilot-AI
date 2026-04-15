from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import Job, User
from app.schemas.common import TaskAcceptedResponse
from app.schemas.job import JobFilter, JobRead
from app.services.task_dispatch import dispatch_task
from app.services.task_logger import create_task_run
from app.tasks.job_tasks import search_jobs_task


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/search", response_model=TaskAcceptedResponse, status_code=202)
def search_jobs(
    payload: JobFilter,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskAcceptedResponse:
    task_run = create_task_run(db, current_user.id, "search_jobs", payload.model_dump())
    dispatch_task(db, task_run, search_jobs_task, task_run.id, current_user.id, payload.model_dump())
    return TaskAcceptedResponse(task_run_id=task_run.id, status=task_run.status, message="Job search queued")


@router.get("", response_model=list[JobRead])
def list_jobs(
    role: str | None = None,
    seniority: str | None = None,
    location: str | None = None,
    remote: bool | None = None,
    salary_min: int | None = Query(default=None, ge=0),
    technologies: str | None = None,
    language: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Job]:
    query = select(Job)
    if role:
        query = query.where(Job.title.ilike(f"%{role}%"))
    if seniority:
        query = query.where(Job.seniority == seniority)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if remote is not None:
        query = query.where(Job.remote_type == ("remote" if remote else "onsite"))
    if salary_min is not None:
        query = query.where(Job.salary_max >= salary_min)
    if language:
        query = query.where(Job.description.ilike(f"%{language}%"))

    jobs = list(db.scalars(query.order_by(Job.created_at.desc())))
    if technologies:
        requested = {value.strip().lower() for value in technologies.split(",") if value.strip()}
        jobs = [
            job
            for job in jobs
            if requested.intersection({technology.lower() for technology in (job.technologies or [])})
        ]
    return jobs


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
