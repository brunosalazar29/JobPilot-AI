from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models import JobMatch, User
from app.schemas.common import TaskAcceptedResponse
from app.schemas.match import JobMatchRead, MatchRunRequest
from app.services.task_dispatch import dispatch_task
from app.services.task_logger import create_task_run
from app.tasks.job_tasks import run_matching_task


router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/run", response_model=TaskAcceptedResponse, status_code=202)
def run_matches(
    payload: MatchRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskAcceptedResponse:
    task_run = create_task_run(db, current_user.id, "run_matching", payload.model_dump())
    dispatch_task(db, task_run, run_matching_task, task_run.id, current_user.id, payload.resume_id, payload.job_ids)
    return TaskAcceptedResponse(task_run_id=task_run.id, status=task_run.status, message="Matching queued")


@router.get("", response_model=list[JobMatchRead])
def list_matches(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[JobMatch]:
    return list(
        db.scalars(
            select(JobMatch)
            .options(selectinload(JobMatch.job))
            .where(JobMatch.user_id == current_user.id)
            .order_by(JobMatch.score.desc(), JobMatch.created_at.desc())
        )
    )


@router.get("/jobs/{job_id}", response_model=JobMatchRead)
def get_match_for_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobMatch:
    match = db.scalar(
        select(JobMatch)
        .options(selectinload(JobMatch.job))
        .where(JobMatch.user_id == current_user.id, JobMatch.job_id == job_id)
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match
